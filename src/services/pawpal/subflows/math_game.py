import json
from typing import List, Literal, Optional
from datetime import datetime, timezone
from pydantic import Field

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from ..agentic import Agentic
from ..schemas.config import ConfigSchema, ConfigurableSchema
from ..schemas.state import SessionState, InterruptSchema
from ..schemas.topic import (
    MathUserAnswerExtraction,
    MathUserAnswer,
    MathQnA,
    TopicResults,
)
from ..utils import PromptLoader


class MGSessionState(SessionState):
    list_qna: List[MathQnA] = []
    start_datetime: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_datetime: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def get_next_question(self, raise_if_none: bool = False) -> Optional[MathQnA]:
        try:
            return next(_qna for _qna in self.list_qna if not _qna.is_answered)
        except StopIteration:
            if raise_if_none:
                raise Exception(
                    f"One of the Math QnA question is empty, please debug why having None:\n{json.dumps([_qna.model_dump(mode='json') for _qna in self.list_qna], indent=2)}"
                )


class MathGame(Agentic):
    COLLECTION_NAME = "math_game-topic"

    @classmethod
    async def _start(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["generate_question"]]:
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            'Introduce the "Math Game" session by telling the ground rule, '
                            "which you will give a analogy of matemathic question based on the provided sequences, "
                            "which only relates to addition and substraction only. "
                            'For example, we will provide you the sequence of "["+4", "-3", "+7", "-2"]", '
                            'and the sum of the sequence which is "6"'
                            "then you will generate the question something like: "
                            '"Andy has 4 apples in his backpack. During his trip, he ate 3 of the apples. '
                            "Then he found the apple tree, collected around 7 apples. "
                            "Finally he arrived at his destination, and gift his mom 2 apple. "
                            'How many apple does Andy has?"'
                            "User will give answer then you need to extract the value."
                        ),
                    },
                    {
                        "type": "text",
                        "text": (
                            "You don't need to give the exact example of math analogy, "
                            "just explain the big picture overall game, so user can understand how to play the game. "
                            "Now introduce the game to the user. Make sure you explain it super simplify."
                        ),
                    },
                ]
            )
        ]
        opening_message = await cls.model.ainvoke([*state.messages, *messages])
        state.add_session(
            session_type="math_games",
            messages=[*messages, opening_message],
        )
        return Command(
            update={
                "list_qna": [],
                "start_datetime": datetime.now(timezone.utc),
                "modified_datetime": datetime.now(timezone.utc),
                "messages": [*messages, opening_message],
                "sessions": state.get_sessions(deep=True),
                "from_node": "start",
                "next_node": "generate_question",
            },
            goto="talk",
        )

    @staticmethod
    async def _talk(state: MGSessionState, config: ConfigSchema):
        """
        Every node that requires interruption for sending/receiving message,
        then it will be directed to this node. Provides the interruption with ease,
        not needing to worry about the interrupt side-effect or best practice to
        put it in beginning of the node.

        This node won't be included into the graph since its just the redirector.
        """
        if state.from_node in ("start", "evaluate", "elaborate"):
            last_ai_msg = state.last_ai_message(
                raise_if_none=True, detail_for_error=state.model_dump(mode="json")
            )
            interrupt([InterruptSchema(action="speaker", message=last_ai_msg.text())])
        elif state.from_node == "ask_question":
            if state.next_node == END:
                last_ai_msg = state.last_ai_message(
                    raise_if_none=True, detail_for_error=state.model_dump(mode="json")
                )
                interrupt(
                    [InterruptSchema(action="speaker", message=last_ai_msg.text())]
                )
            else:
                # actually this is redundant, but its oke la, make it more clearer if something change might happen in the future
                qna: MathQnA = state.get_next_question(raise_if_none=True)
                interrupt([InterruptSchema(action="speaker", message=qna.question)])
        return Command(goto=state.next_node)

    @classmethod
    async def _generate_question(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["ask_question"]]:
        configurable = config["configurable"]
        _curr_config = configurable["feature_params"]["math_game"]
        total_question = _curr_config["total_question"]
        LENGTH_RANGE, MIN_VAL, MAX_VAL, NO_SUM_BELOW_ZERO = (    # TODO: later remove, need to add as the mathgame param
            lambda: 2,  # TODO: will use the random length from topic params, currently for MVP purposes
            -3,
            8,
            True,
        )  # generate param for difficulty
        list_qna: List[MathQnA] = [
            MathQnA(
                sequence=(
                    MathQnA.generate_sequence(
                        length=LENGTH_RANGE(),  # TODO: later remove
                        min_val=MIN_VAL,
                        max_val=MAX_VAL,
                        no_sum_below_zero=NO_SUM_BELOW_ZERO,
                    )
                )
            )
            for _ in range(total_question)
        ]

        for _qna in list_qna:
            if _qna.question is not None:
                continue

            _temp_messages = [
                SystemMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                f"You will be provided number of sequence with length of {len(_qna.sequence)} and the sum of the sequence. "
                                "The sequence will consist of addition and substraction which in the end leads to the sum. "
                                "Your task will be generate matemathic question in analogy concepts then ask the user for answer. "
                                "Example: "
                                'You will be provided with sequence, such as "["+4", "+3", "-1"]" with the sum of "+6". '
                                "Then you can generate analogy matemathic question such as: "
                                '\n"'
                                "You have 4 apples in your bag. On your journey, you found another 3 apples,"
                                "and you see a cute horse, you gave him one of your apples."
                                '"\n'
                                "Then you ask the user for the right sum of apples they have"
                                "\n\n"
                                "Should the sum be a negative value, use metrics in your analogy that *can* have a negative value."
                                "Example:"
                                "\n\n"
                                "If your final value is negative, do NOT use number of objects! It is illogical to have a negative number of objects."
                                "Use something else such as temperature."
                                "Ensure that your analogy is easily understood by children aged 4-8 years old."
                                "Example:"
                                "✅ Good analogy: Depicting values in generic metrics, e.g. as a number of apples, marbles, friends, etc."
                                "❌ Bad analogy: Complex, highly scientific or domain-exclusive metrics, such as pH, distance, temperature, etc."
                                "Remember that the child is aged 4-8 years old; **they most likely lack a knowledge base for common metrics such as 1000m equating to 1km, ratios, percentages, etc. Refrain from referring to those!**"

                                "\n# DO NOT SHOW THE ANSWER IN THE QUESTION, ITS JUST A QUESTION."
                                "**YOUR ANALOGY SHOULD NOT DEPICT ANY ILLEGAL, VIOLENT, HARMFUL, POLITICAL, OR ANY OTHERWISE UNSAFE ANALOGIES SUCH AS STEALING, KILLING, VIOLENCE TOWARD HUMANS OR ANIMALS, ETC.** "
                                "\n# THE PROVIDED SEQUENCE IS JUST A WAY TO STRUCTURE YOUR QUESTION, USE THE ANALOGY INSTEAD SHOWING THE NUMBER FULLY LIKE ARITHMETIC."
                            ),
                        }
                    ]
                ),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                f"Generate the math analogy using the provided sequence: {_qna.fmt_sequence()}, "
                                f'and the sum of the sequence is "{_qna.answer}". '
                                "The sum is only for showing you the answer, you are not suppose to show the answer or any explanation. "
                                "Just provide the analogy question, don't use any literal number instead use in words, "
                                "e.g. instead of '1' write it as 'one', '2' as 'two', '24' as 'twenty four', and so on. "
                                "The ANALOGY OBJECT you are using must be CONSISTENT across the story.\n"
                                "MAKE THE ANALOGY SHORT & CONCISE, IT'S RANGING EITHER ONE OR TWO SENTENCES."  #   # TODO: later remove, temporary just to make it short
                            )
                            + PromptLoader().language_template.format(
                                user_language=configurable["user"].get(
                                    "language", "English"
                                )
                            ),
                        }
                    ]
                ),
            ]
            _llm_question = await cls.model.ainvoke(_temp_messages)
            _qna.question = _llm_question.text()

        print(
            "Generated MathQnA:",
            json.dumps([i.model_dump(mode="json") for i in list_qna], indent=2),
        )

        return Command(
            update={
                "modified_datetime": datetime.now(timezone.utc),
                "list_qna": list_qna,
                "from_node": "generate_question",
                "next_node": "ask_question",
            },
            goto="ask_question",
        )

    @classmethod
    async def _ask_question(cls, state: MGSessionState, config: ConfigSchema) -> Command[Literal["listening", END]]:  # type: ignore
        configurable = config["configurable"]
        last_session = state.verify_last_session(session_type="math_games")

        qna = state.get_next_question()
        modified_datetime = datetime.now(timezone.utc)
        if qna is not None:
            qna_messages = [AIMessage(content=[{"type": "text", "text": qna.question}])]
            state.add_message_to_last_session(
                session_type="math_games",
                messages=qna_messages,
            )
            print(
                "DEBUG MATHQNA ASK:", json.dumps(qna.model_dump(mode="json"), indent=2)
            )
            return Command(
                update={
                    "modified_datetime": modified_datetime,
                    "messages": qna_messages,
                    "sessions": state.get_sessions(deep=True),
                    "from_node": "ask_question",
                    "next_node": "listening"
                },
                goto="talk",
            )

        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "Tell the child that the current session is ending."
                            "You must say thank you for participating for the session. You look forward to the next Math Adventures session with the child."
                            "Congratulate and praise the child if they did good during the session."
                            "Otherwise, cheer and motivate the child to play with you again."
                            "**DO NOT END YOUR RESPONSE WITH A QUESTION.**"
                            "Your whole response must not exceed 20 words."
                            "Example:"
                            "'Wah, sudah selesai sesi Math Adventures kita hari ini! Terima kasih karena sudah mau main denganku, dan congrats karena kamu sudah menjawab banyak pertanyaan dengan benar. Kamu hebat! Sampai ketemu di sesi selanjutnya yaa!'"
                            + "\n"
                            + "\n"
                            + PromptLoader().language_template.format(
                                user_language=configurable["user"].get(
                                    "language", "English"
                                )
                            )
                        ),
                    }
                ]
            ),
        ]
        end_conversation_message = await cls.model.ainvoke([*state.messages, *messages])
        state.add_message_to_last_session(
            session_type="math_games",
            messages=[*messages, end_conversation_message],
        )
        model_with_session_result = cls.model.with_structured_output(
            TopicResults.MathGameResult._Extraction
        )
        _extracted_result: TopicResults.MathGameResult._Extraction = (
            await model_with_session_result.ainvoke(last_session.get_messages())
        )

        state.add_result_to_last_session(
            session_type="math_games",
            result=TopicResults.MathGameResult(
                extraction=_extracted_result,
                list_qna=state.list_qna,
                start_datetime=state.start_datetime,
                modified_datetime=modified_datetime,
            ),
        )
        return Command(
            update={
                "modified_datetime": modified_datetime,
                "messages": [*messages, end_conversation_message],
                "sessions": state.get_sessions(deep=True),
                "from_node": "ask_question",
                "next_node": END,
            },
            goto="talk",
        )

    @classmethod
    async def _listening(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["evaluate"]]:
        configurable = config["configurable"]
        _ = state.verify_last_session(session_type="math_games")
        user_response: str = interrupt([InterruptSchema(action="microphone")])
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "Extract the answer from the user response, "
                            "the expected answer will be number. "
                            f"This number can be defined as literal decimal or number in words that can be in English language or {configurable['user']['language']} language."
                        ),
                    }
                ]
            ),
            HumanMessage(content=[{"type": "text", "text": user_response}]),
        ]
        state.add_message_to_last_session(
            session_type="math_games",
            messages=messages,
        )
        model_with_math_user_answer = cls.model.with_structured_output(
            MathUserAnswerExtraction
        )
        _math_extracted_result: MathUserAnswerExtraction = (
            await model_with_math_user_answer.ainvoke(messages)
        )
        qna: MathQnA = state.get_next_question(raise_if_none=True)
        qna.user_answers.append(
            MathUserAnswer(raw_answer=user_response, extraction=_math_extracted_result)
        )
        return Command(
            update={
                "modified_datetime": datetime.now(timezone.utc),
                "messages": messages,
                "sessions": state.get_sessions(deep=True),
                "from_node": "listening",
                "next_node": "evaluate",
            },
            goto="evaluate",
        )

    @classmethod
    async def _evaluate(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["listening", "elaborate", "ask_question"]]:
        _ = state.verify_last_session(session_type="math_games")
        qna: MathQnA = state.get_next_question(raise_if_none=True)
        if not qna.user_answers:
            raise Exception(f"mathgame: how no user answer {qna}\nstate: {state}")

        print("DEBUG MATHQNA EVAL:", json.dumps(qna.model_dump(mode="json"), indent=2))
        if qna.is_correct():
            qna.is_answered = True
            next_node = "ask_question"
            messages = [
                SystemMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                "Congratulate the child for answering the answer correctly. "
                                "Praise them because they are hardworking for solving the question."
                                "Your response should not exceed 15 words."
                                "DON'T ASK ANOTHER QUESTION OR MOTIVATE THE USER, YOUR JOB ONLY CONGRATULATE."
                                "Example:"
                                "Benar sekali Adik! Selamat! Kamu sangat hebat, pasti belajarnya rajin yaa."
                                "You are free to come up with more sentences that are similar in nature and tone to the above."
                            ),
                        }
                    ]
                )
            ]
        else:
            latest_user_answer = qna.latest_user_answer
            next_node = "listening"
            if latest_user_answer is None:
                messages = [
                    SystemMessage(
                        content=[
                            {
                                "type": "text",
                                "text": (
                                    "Encourage the child to come out of their shell and answer."
                                    "Reassure them that it's ok if their answer is right or wrong."
                                    "Emphasize that PawPal is the child's companion who learns alongside themselves, not someone who punishes wrong answers."
                                    "Your response should not exceed 15 words."
                                    "JUST ENCOURAGEMENT, DON'T GIVE OUT THE ANSWER OR ANY CLUE."
                                    "DON'T ASK ANOTHER QUESTION, YOUR JOB ONLY TO ENCOURAGE THE CHILD TO ANSWER. "
                                    "Example:"
                                    "Kalo menurut kamu jawabannya berapa? Gak apa-apa kalau salah, kita belajar bareng di sini!"
                                    "You are free to come up with more sentences that are similar in nature and tone to the above."
                                ),
                            }
                        ]
                    )
                ]
            else:
                messages = [
                    SystemMessage(
                        content=[
                            {
                                "type": "text",
                                "text": (
                                    "Gently tell the child that their answer was INCORRECT."
                                    "Reassure the child that it's ok that they answered incorrectly."
                                    "Emphasize that PawPal is the child's companion who learns alongside themselves, not someone who punishes wrong answers."
                                    "Encourage the user to think step by step, and never give up."
                                    "JUST ENCOURAGEMENT, DON'T GIVE OUT THE ANSWER OR ANY CLUE. "
                                    "DON'T ASK ANOTHER QUESTION, YOUR JOB ONLY TO MOTIVATE THE CHILD TO ANSWER AGAIN. "
                                    "Example:"
                                    "Kayaknya jawaban kamu masih belum tepat. Tidak apa-apa, yuk kita coba lagi!"
                                    "You are free to come up with more sentences that are similar in nature and tone to the above."
                                ),
                            }
                        ]
                    )
                ]

            if len(qna.user_answers) >= 3:  # end the trial
                next_node = "elaborate"

        evaluate_response = await cls.model.ainvoke([*state.messages, *messages])
        qna.user_answers[-1].feedback = evaluate_response.text()
        state.add_message_to_last_session(
            session_type="math_games",
            messages=[*messages, evaluate_response],
        )
        return Command(
            update={
                "list_qna": state.list_qna,
                "modified_datetime": datetime.now(timezone.utc),
                "messages": [*messages, evaluate_response],
                "sessions": state.get_sessions(deep=True),
                "from_node": "evaluate",
                "next_node": next_node,
            },
            goto="talk",
        )

    @classmethod
    async def _elaborate(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["ask_question"]]:
        _ = state.verify_last_session(session_type="math_games")
        qna = state.get_next_question(raise_if_none=True)
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Elaborate and explain how to solve the question step by step.",
                    }
                ]
            ),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            f"The question is '{qna.question}', can you help elaborate to me the thinking? "
                            f"Try explain in effective manner, short and concise, while in the end you will provide the answer which is '{qna.answer}'. "
                            f"EXPLAIN IT IN SHORT WAY, DON'T OVER-EXPLAIN, meanwhile provide the ANSWER in the END which is '{qna.answer}'. "
                            f"PLEASE PROVIDE THE ANSWER IS '{qna.answer}'"
                        ),
                    }
                ]
            ),
        ]
        elaborate_response = await cls.model.ainvoke([*state.messages, *messages])
        state.add_message_to_last_session(
            session_type="math_games",
            messages=[*messages, elaborate_response],
        )
        return Command(
            update={
                "modified_datetime": datetime.now(timezone.utc),
                "messages": [*messages, elaborate_response],
                "sessions": state.get_sessions(deep=True),
                "from_node": "elaborate",
                "next_node": "ask_question",
            },
            goto="talk",
        )

    @classmethod
    def build_workflow(cls) -> CompiledStateGraph:
        builder = StateGraph(
            MGSessionState, input=SessionState, config_schema=ConfigurableSchema
        )

        # Node
        builder.add_node("start", cls._start)
        builder.add_node("talk", cls._talk)
        builder.add_node("generate_question", cls._generate_question)
        builder.add_node("ask_question", cls._ask_question)
        builder.add_node("listening", cls._listening)
        builder.add_node(
            "evaluate", cls._evaluate
        )  # will contain eval, try again, congratz
        builder.add_node("elaborate", cls._elaborate)

        # Edge
        builder.add_edge(START, "start")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
