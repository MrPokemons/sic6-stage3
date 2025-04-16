from typing import Dict

from .talk_to_me import TalkToMe as TalkToMeFlow
from .math_game import MathGame as MathGamesFlow
from .spelling_game import SpellingGame as SpellingGamesFlow
from .would_you_rather import WouldYouRather as WouldYouRatherFlow

from ..agentic import Agentic
from ..schemas.topic_flow import TopicFlowType

__all__ = ["TalkToMeFlow", "MathGamesFlow", "SpellingGamesFlow", "WouldYouRatherFlow"]

TopicFlowClassMapping: Dict[TopicFlowType, Agentic] = {
    "talk_to_me": TalkToMeFlow,
    "math_games": MathGamesFlow,
    "spelling_games": SpellingGamesFlow,
    "would_you_rather": WouldYouRatherFlow,
}
