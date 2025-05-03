import json
from typing import List, Literal, Optional
from datetime import datetime, timezone
from pydantic import Field

from langchain_core.messages import SystemMessage, HumanMessage
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
from ..utils import prompt_loader


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
                raise_if_none=True, details=state.model_dump(mode="json")
            )
            interrupt([InterruptSchema(action="speaker", message=last_ai_msg.text())])
        elif state.from_node == "ask_question":
            if state.next_node == END:
                last_ai_msg = state.last_ai_message(
                    raise_if_none=True, details=state.model_dump(mode="json")
                )
                interrupt(
                    [InterruptSchema(action="speaker", message=last_ai_msg.text())]
                )
            else:
                qna: MathQnA = state.get_next_question(raise_if_none=True)
                interrupt([InterruptSchema(action="speaker", message=qna.question)])
        return Command(goto=state.next_node)

    @classmethod
    async def _generate_question(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["ask_question"]]:
        _curr_config = config["configurable"]["feature_params"]["math_game"]
        total_question = _curr_config["total_question"]
        LENGTH, MIN_VAL, MAX_VAL = 5, -5, 5  # generate
        list_qna: List[MathQnA] = [
            MathQnA(
                sequence=(
                    MathQnA.generate_sequence(
                        length=LENGTH, min_val=MIN_VAL, max_val=MAX_VAL
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
                                'You will be provided with sequence, such as "["+4", "+3", "-1", "+5", "-4"]" with the sum of "+7". '
                                "Then you can generate analogy matemathic question such as: "
                                '\n"'
                                "You have 4 apples in your bag. On your journey, you found another 3 apples,"
                                "and you see a cute horse, you gave one of your apple. "
                                "After you returned home, your mother gifted you 5 additional apple."
                                "Finally to reward youself, you ate 4 apples you have taken along the way."
                                '"\n'
                                "Then you ask the user for the right sum of apples they have"
                                "\n\n"
                                "If the sum if negative, use another type of analogy that are plausible to be have negative value, "
                                "which making the user understand the matemathic analogy, such as Temperature, Money, Height like in a Elevator or on a Mountain, etc. "
                                "Make sure your analogy is very easy to understand, since it's for children"
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
                                f'and the sum of the sequence is "{_qna.answer}".'
                            ),
                        }
                    ]
                ),
            ]
            _llm_question = await cls.model.ainvoke(_temp_messages)
            _qna.question = _llm_question.text()

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
        qna = state.get_next_question()
        if qna is not None:
            return Command(
                update={"from_node": "ask_question", "next_node": "listening"},
                goto="listening",
            )

        last_session = state.verify_last_session(session_type="math_games")
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "End the Session, while saying thank you for participating for the session."
                            + "\n"
                            + prompt_loader.language_template.format(
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

        modified_datetime = datetime.now(timezone.utc)
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
        _ = state.verify_last_session(session_type="math_games")
        user_response: str = interrupt([InterruptSchema(action="microphone")])
        messages = [HumanMessage(content=[{"type": "text", "text": user_response}])]
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
        if qna.is_correct():
            qna.is_answered = True
            next_node = "ask_question"
            messages = [
                SystemMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                "Congratulate user for answering the answer correctly and accurately. "
                                "Praise his/hers hardworking for solving the question."
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
                                    "Motivate the user to answer, telling don't gives up, and lets answer correctly"
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
                                    "Tell the user the answer is wrong, and let's take another chance to solve the question. "
                                    "Encourage to think step by step, and don't give up."
                                ),
                            }
                        ]
                    )
                ]

            if len(qna.user_answers) >= 3:  # end the trial
                next_node = "elaborate"

        evaluate_response = await cls.model.ainvoke([*state.messages, *messages])
        state.add_message_to_last_session(
            session_type="math_games",
            messages=[*messages, evaluate_response],
        )
        return Command(
            update={
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
                            f"The question is {qna.question}, can you help elaborate to me the thinking? "
                            "Try explain in very-very efficient manner. "
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
    def build_workflow(self) -> CompiledStateGraph:
        builder = StateGraph(
            MGSessionState, input=SessionState, config_schema=ConfigurableSchema
        )

        # Node
        builder.add_node("start", self._start)
        builder.add_node("talk", self._talk)
        builder.add_node("generate_question", self._generate_question)
        builder.add_node("ask_question", self._ask_question)
        builder.add_node("listening", self._listening)
        builder.add_node(
            "evaluate", self._evaluate
        )  # will contain eval, try again, congratz
        builder.add_node("elaborate", self._elaborate)

        # Edge
        builder.add_edge(START, "start")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
