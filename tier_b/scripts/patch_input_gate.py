"""Adds an optional separate input gate to MLVC's decoder memory (DMC-6.1sb).

Off by default (model.p_frame.input_gate: false), so other runs are unchanged.
With input_gate on, the memory update becomes  m = f*m + i*s  instead of  m = f*m + (1-f)*s.
When loading a checkpoint without the input-gate channels, the new channels are
initialised as the negated forget-gate channels, so with hard_sigmoid the model starts
exactly equal to the loaded one (hard_sigmoid(-x) = 1 - hard_sigmoid(x)).
Usage: python patch_input_gate.py <path to mlvc/video>   (safe to run more than once)
"""
import os
import sys

root = sys.argv[1]
model_py = os.path.join(root, "src", "models", "dmc_6", "dmc_61sb.py")
factory_py = os.path.join(root, "src", "utils", "model_factory.py")


def patch(path, edits):
    text = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    if "input_gate" in text:
        print("already patched:", os.path.basename(path))
        return
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"patch anchor not found exactly once in {path}: {old[:60]!r}")
        text = text.replace(old, new)
    open(path, "w", encoding="utf-8").write(text)
    print("patched:", os.path.basename(path))


patch(model_py, [
    (
        "        gate_activation: str,\n        network_mode: NetworkMode,\n    ):\n        super().__init__()\n\n        block_args",
        "        gate_activation: str,\n        network_mode: NetworkMode,\n        input_gate: bool = False,\n    ):\n        super().__init__()\n\n        block_args",
    ),
    (
        "        self.conv2 = DMCConv2d(mid_ch, 3 * out_ch, 1, **conv_args)",
        "        self.input_gate = input_gate\n        self.out_ch = out_ch\n"
        "        self.conv2 = DMCConv2d(mid_ch, (4 if input_gate else 3) * out_ch, 1, **conv_args)",
    ),
    (
        "        state, forget_gate, output_gate = torch.chunk(feature, 3, dim=1)\n"
        "        forget_gate = self.gate_activation(forget_gate)\n"
        "        output_gate = self.gate_activation(output_gate)\n"
        "        state = self.memory_activation(state)\n\n"
        "        memory = forget_gate * memory + (1 - forget_gate) * state\n",
        "        if self.input_gate:\n"
        "            state, forget_gate, output_gate, input_gate = torch.chunk(feature, 4, dim=1)\n"
        "            input_gate = self.gate_activation(input_gate)\n"
        "        else:\n"
        "            state, forget_gate, output_gate = torch.chunk(feature, 3, dim=1)\n"
        "        forget_gate = self.gate_activation(forget_gate)\n"
        "        output_gate = self.gate_activation(output_gate)\n"
        "        state = self.memory_activation(state)\n\n"
        "        if self.input_gate:\n"
        "            memory = forget_gate * memory + input_gate * state\n"
        "        else:\n"
        "            memory = forget_gate * memory + (1 - forget_gate) * state\n",
    ),
    (
        "        return feature, memory\n",
        "        return feature, memory\n\n"
        "    def _load_from_state_dict(self, state_dict, prefix, *args, **kwargs):\n"
        "        if self.input_gate:\n"
        "            c = self.out_ch\n"
        "            for name in (\"conv2.weight\", \"conv2.bias\"):\n"
        "                key = prefix + name\n"
        "                if key in state_dict and state_dict[key].shape[0] == 3 * c:\n"
        "                    t = state_dict[key]\n"
        "                    state_dict[key] = torch.cat((t, -t[c:2 * c]), dim=0)\n"
        "        super()._load_from_state_dict(state_dict, prefix, *args, **kwargs)\n",
    ),
    (
        '        gate_activation: str = "sigmoid",\n',
        '        gate_activation: str = "sigmoid",\n        input_gate: bool = False,\n',
    ),
    (
        "            gate_activation=gate_activation,\n",
        "            gate_activation=gate_activation,\n            input_gate=input_gate,\n",
    ),
])

patch(factory_py, [
    (
        '            gate_activation=config.get("gate_activation", "sigmoid"),\n',
        '            gate_activation=config.get("gate_activation", "sigmoid"),\n'
        '            input_gate=config.get("input_gate", False),\n',
    ),
])
