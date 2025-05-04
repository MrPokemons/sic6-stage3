import json
from typing import List, Literal, Optional, Dict
from pathlib import Path
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
    GuessTheSoundUserAnswerExtraction,
    GuessTheSoundUserAnswer,
    GuessTheSoundQnA,
    TopicResults,
)
from ..utils import PromptLoader


ROOT_PATH = Path(__file__).parents[4]
GUESS_THE_SOUND_AUDIO_PATH = ROOT_PATH / "data" / "guess_the_sound"

GUESS_THE_SOUND_MAPPING: Dict[str, List[Path]] = {}  # name -> list path
for fn in GUESS_THE_SOUND_AUDIO_PATH.iterdir():
    target_obj, _index_dot_ext = fn.name.split("_", 1)
    if target_obj not in GUESS_THE_SOUND_MAPPING:
        GUESS_THE_SOUND_MAPPING[target_obj] = []
    GUESS_THE_SOUND_MAPPING[target_obj].append(fn.absolute())


class GTSSessionState(SessionState):
    list_qna: List[GuessTheSoundQnA] = []
    start_datetime: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_datetime: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def get_next_question(
        self, raise_if_none: bool = False
    ) -> Optional[GuessTheSoundQnA]:
        try:
            return next(_qna for _qna in self.list_qna if not _qna.is_answered)
        except StopIteration:
            if raise_if_none:
                raise Exception(
                    f"One of the Guess the Sound QnA question is empty, please debug why having None:\n{json.dumps([_qna.model_dump(mode='json') for _qna in self.list_qna], indent=2)}"
                )


class GuessTheSound(Agentic):
    COLLECTION_NAME = "guess_the_sound-topic"

    @classmethod
    async def _start(
        cls, state: GTSSessionState, config: ConfigSchema
    ) -> Command[Literal["generate_question"]]:
        configurable = config["configurable"]
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            'Introduce the "Guess the Sound" session by telling the ground rule, '
                            "Which the system will play random sound, and the user must predict what it is based on the audio."
                            "Now introduce the session to the user. Make sure you explain it super simplify. "
                            "EXPLAIN IN ONE OR TWO SENTENCES."
                            "**YOU DON'T MAKE THE QUESTION**"
                        )
                        + "\n"
                        + PromptLoader().language_template.format(
                            user_language=configurable["user"].get(
                                "language", "English"
                            )
                        ),
                    },
                ]
            )
        ]
        opening_message = await cls.model.ainvoke([*state.messages, *messages])
        state.add_session(
            session_type="guess_the_sound",
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
    async def _talk(state: GTSSessionState, config: ConfigSchema):
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
            last_ai_msg = state.last_ai_message(
                raise_if_none=True, detail_for_error=state.model_dump(mode="json")
            )
            interrupt([InterruptSchema(action="speaker", message=last_ai_msg.text())])
            if state.next_node != END:  # sending the animal sound
                qna: GuessTheSoundQnA = state.get_next_question(raise_if_none=True)
                interrupt(
                    [
                        InterruptSchema(
                            action="speaker+audio", message=str(qna.sound_path)
                        )
                    ]
                )

        return Command(goto=state.next_node)

    @classmethod
    async def _generate_question(
        cls, state: GTSSessionState, config: ConfigSchema
    ) -> Command[Literal["ask_question"]]:
        configurable = config["configurable"]
        _curr_config = configurable["feature_params"]["guess_the_sound"]
        total_question = _curr_config["total_question"]
        list_qna: List[GuessTheSoundQnA] = []

        for _ in range(total_question):
            obj_, obj_sound_path = GuessTheSoundQnA.randomize_gts_mapping(
                gts_mapping=GUESS_THE_SOUND_MAPPING,
            )
            _qna = GuessTheSoundQnA(sound_path=obj_sound_path, answer=obj_)
            list_qna.append(_qna)

        print(
            "Generated GTSQnA:",
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
    async def _ask_question(cls, state: GTSSessionState, config: ConfigSchema) -> Command[Literal["listening", END]]:  # type: ignore
        configurable = config["configurable"]
        qna = state.get_next_question()
        modified_datetime = datetime.now(timezone.utc)
        last_session = state.verify_last_session(session_type="guess_the_sound")
        if qna is not None:
            messages = [
                SystemMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                "Tell the user to guess the sound play after this, "
                                "make it very-very short"
                            )
                            + "\n"
                            + PromptLoader().language_template.format(
                                user_language=configurable["user"].get(
                                    "language", "English"
                                )
                            ),
                        }
                    ]
                )
            ]
            bridging_question = await cls.model.ainvoke([*state.messages, *messages])
            state.add_message_to_last_session(
                session_type="guess_the_sound", messages=[*messages, bridging_question]
            )
            print(
                "DEBUG GTSQNA ASK:", json.dumps(qna.model_dump(mode="json"), indent=2)
            )
            return Command(
                update={
                    "modified_datetime": modified_datetime,
                    "messages": [*messages, bridging_question],
                    "sessions": state.get_sessions(deep=True),
                    "from_node": "ask_question",
                    "next_node": "listening",
                },
                goto="talk",
            )

        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "End the Session, while saying thank you for participating for the session."
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
            session_type="guess_the_sound",
            messages=[*messages, end_conversation_message],
        )
        model_with_session_result = cls.model.with_structured_output(
            TopicResults.GuessTheSoundResult._Extraction
        )
        _extracted_result: TopicResults.GuessTheSoundResult._Extraction = (
            await model_with_session_result.ainvoke(last_session.get_messages())
        )

        state.add_result_to_last_session(
            session_type="guess_the_sound",
            result=TopicResults.GuessTheSoundResult(
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
        cls, state: GTSSessionState, config: ConfigSchema
    ) -> Command[Literal["evaluate"]]:
        configurable = config["configurable"]
        _ = state.verify_last_session(session_type="guess_the_sound")
        user_response: str = interrupt([InterruptSchema(action="microphone")])
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "Extract the answer from the user response, "
                            f"the expected answers will be either from following: {json.dumps(list(GUESS_THE_SOUND_MAPPING))}. "
                            "CLASSIFY EITHER OF THE USER EXTRACTED ANSWER FROM THE ABOVE PROVIDED LIST OF ANSWERS. "
                            "IF THE USER'S ANSWER IS VERY UNRELATED FROM THE PROVIDED LIST OF ANSWERS, CONSIDER AS NONE FOR MARKING WRONG. "
                            f"The answer can be either English language or {configurable['user']['language']} language."
                        ),
                    }
                ]
            ),
            HumanMessage(content=[{"type": "text", "text": user_response}]),
        ]
        state.add_message_to_last_session(
            session_type="guess_the_sound",
            messages=messages,
        )
        model_with_gts_user_answer = cls.model.with_structured_output(
            GuessTheSoundUserAnswerExtraction
        )
        _gts_extracted_result: GuessTheSoundUserAnswerExtraction = (
            await model_with_gts_user_answer.ainvoke(messages)
        )
        qna: GuessTheSoundQnA = state.get_next_question(raise_if_none=True)
        qna.user_answers.append(
            GuessTheSoundUserAnswer(
                raw_answer=user_response, extraction=_gts_extracted_result
            )
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
        cls, state: GTSSessionState, config: ConfigSchema
    ) -> Command[Literal["listening", "elaborate", "ask_question"]]:
        _ = state.verify_last_session(session_type="guess_the_sound")
        qna: GuessTheSoundQnA = state.get_next_question(raise_if_none=True)
        if not qna.user_answers:
            raise Exception(f"guessTheSound: how no user answer {qna}\nstate: {state}")

        print("DEBUG GTSQNA EVAL:", json.dumps(qna.model_dump(mode="json"), indent=2))
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
                                "Praise his/hers hardworking for solving the question. "
                                "DON'T ASK ANOTHER QUESTION, YOUR JOB ONLY CONGRATULATE. "
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
                                    "Encourage the user to try to answer, just encourage words and tell him/her to try again. "
                                    "JUST ENCOURAGEMENT, DON'T GIVE OUT THE ANSWER OR ANY CLUE."
                                    "DON'T ASK ANOTHER QUESTION, YOUR JOB ONLY ENCOURAGE. "
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
                                    "Inform the user that their answer is WRONG. Motivate them to try again since there's still available attempt. "
                                    "Encourage the user to analyze better, and never give up. "
                                    "JUST ENCOURAGEMENT, DON'T GIVE OUT THE ANSWER OR ANY CLUE. "
                                    "DON'T ASK ANOTHER QUESTION, YOUR JOB ONLY MOTIVATE. "
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
            session_type="guess_the_sound",
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
        cls, state: GTSSessionState, config: ConfigSchema
    ) -> Command[Literal["ask_question"]]:
        _ = state.verify_last_session(session_type="guess_the_sound")
        qna = state.get_next_question(raise_if_none=True)
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Try to explain what sound it is, and why. "
                        "Just in a SHORT WAY DONT OVER EXPLAIN, MAX SENTENCES IS ONE OR TWO.",
                    }
                ]
            ),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            f"The answer is '{qna.answer}' sound, how should I identify that?"
                        ),
                    }
                ]
            ),
        ]
        elaborate_response = await cls.model.ainvoke([*state.messages, *messages])
        state.add_message_to_last_session(
            session_type="guess_the_sound",
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
            GTSSessionState, input=SessionState, config_schema=ConfigurableSchema
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
