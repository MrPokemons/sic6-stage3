from typing import Dict

from .talk_to_me import TalkToMe as TalkToMeFlow
from .math_game import MathGame as MathGamesFlow
from .guess_the_sound import GuessTheSound as GuessTheSoundFlow
from .would_you_rather import WouldYouRather as WouldYouRatherFlow

from ..agentic import Agentic
from ..schemas.topic_flow import TopicFlowType

__all__ = ["TalkToMeFlow", "MathGamesFlow", "GuessTheSoundFlow", "WouldYouRatherFlow"]

TopicFlowClassMapping: Dict[TopicFlowType, Agentic] = {
    "talk_to_me": TalkToMeFlow,
    "math_games": MathGamesFlow,
    "guess_the_sound": GuessTheSoundFlow,
    "would_you_rather": WouldYouRatherFlow,
}
