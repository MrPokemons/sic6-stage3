from typing import List, Literal
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
from ..schemas.topic import MathQnA, TopicResults


class MGSessionState(SessionState):
    list_qna: List[MathQnA] = []
    start_datetime: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_datetime: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
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
        if state.from_node in ("start", "generate_question"):
            last_ai_msg = state.last_ai_message()
            if last_ai_msg is None:
                raise Exception(
                    f"How no last ai message? {state.model_dump(mode='json')}"
                )
            interrupt([InterruptSchema(action="speaker", message=last_ai_msg.text())])
        elif state.from_node == "check_session":
            if state.next_node == END:
                last_ai_msg = state.last_ai_message()
                if last_ai_msg is None:
                    raise Exception(
                        f"How no last ai message? {state.model_dump(mode='json')}"
                    )
                interrupt(
                    [InterruptSchema(action="speaker", message=last_ai_msg.text())]
                )
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
                "list_qna": list_qna,
                "sessions": state.get_sessions(deep=True),
                "from_node": "generate_question",
                "next_node": "ask_question",
            },
            goto="ask_question",
        )

    @classmethod
    async def _ask_question(cls, state: MGSessionState, config: ConfigSchema) -> Command[Literal["listening", END]]:  # type: ignore
        ...

    @classmethod
    async def _listening(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["evaluate"]]: ...

    @classmethod
    async def _evaluate(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["evaluate", "elaborate", "ask_question"]]: ...

    @classmethod
    async def _elaborate(
        cls, state: MGSessionState, config: ConfigSchema
    ) -> Command[Literal["ask_question"]]: ...

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
