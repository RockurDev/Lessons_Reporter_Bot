import json
from ast import TypeVar
from dataclasses import dataclass, field
from functools import partial
from typing import Callable

Callback = Callable[..., None]
CallbackType = TypeVar('CallbackType', bound=Callback)


@dataclass
class CallbackStorage:
    callbacks_version: str
    callbacks: list[Callback] = field(default_factory=list)

    def register(self, callback: CallbackType) -> CallbackType:
        assert callback not in self.callbacks
        self.callbacks.append(callback)
        return callback

    def to_callback_data(self, callback_partial: partial[Callback]) -> str:
        assert not callback_partial.keywords
        idx = self.callbacks.index(callback_partial.func)
        dumped_items = [
            self.callbacks_version,
            str(idx),
            *(json.dumps(item).replace('\n', '\\\n') for item in callback_partial.args),
        ]
        return '\n'.join(dumped_items)

    def from_callback_data(self, callback_data: str) -> partial[Callback]:
        dumped_items = callback_data.splitlines()
        callbacks_version, idx, partial_args = (
            dumped_items[0],
            int(dumped_items[1]),
            [json.loads(item.replace('\\\n', '\n')) for item in dumped_items[2:]],
        )

        if callbacks_version != self.callbacks_version:
            print('received callback data with wrong version', callback_data)
            return partial(lambda: None)

        return partial(self.callbacks[idx], *partial_args)
