from typing import TypeAlias, Literal, Dict

from ..agentic import Agentic
from .talk_to_me import TalkToMe as TalkToMeFlow
from .math_game import MathGame as MathGamesFlow
from .spelling_game import SpellingGame as SpellingGamesFlow
from .would_you_rather import WouldYouRather as WouldYouRatherFlow


__all__ = ["TalkToMeFlow", "MathGamesFlow", "SpellingGamesFlow", "WouldYouRatherFlow"]

FlowFeatureType: TypeAlias = Literal[
    "talk_to_me", "math_games", "spelling_games", "would_you_rather"
]
FlowFeatureNodeType: TypeAlias = Literal[
    "talk_to_me_flow", "math_games_flow", "spelling_games_flow", "would_you_rather_flow"
]
FlowFeatureNodeMapping: Dict[FlowFeatureType, FlowFeatureNodeType] = {
    _name: _node
    for _name, _node in zip(FlowFeatureType.__args__, FlowFeatureNodeType.__args__)
}
FlowFeatureClassMapping: Dict[FlowFeatureType, Agentic] = {
    "talk_to_me": TalkToMeFlow,
    "math_games": MathGamesFlow,
    "spelling_games": SpellingGamesFlow,
    "would_you_rather": WouldYouRatherFlow,
}
