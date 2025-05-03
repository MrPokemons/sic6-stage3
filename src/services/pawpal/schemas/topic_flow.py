from typing import TypeAlias, Literal, Dict


TopicFlowType: TypeAlias = Literal[
    "talk_to_me", "math_games", "guess_the_sound", "would_you_rather"
]
TopicFlowNodeType: TypeAlias = Literal[
    "talk_to_me_flow", "math_games_flow", "guess_the_sound_flow", "would_you_rather_flow"
]
TopicFlowNodeMapping: Dict[TopicFlowType, TopicFlowNodeType] = {
    _name: _node
    for _name, _node in zip(TopicFlowType.__args__, TopicFlowNodeType.__args__)
}
