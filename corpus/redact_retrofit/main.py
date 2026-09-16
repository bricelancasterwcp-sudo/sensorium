"""Not a seeded bug: this case demonstrates the retrofit (`sensorium redact`)
over a trace recorded with the rule OFF, rather than rule v1's name rule at
recording time -- that is `secret_in_env`'s case. `SENSORIUM_NO_REDACT: "1"`
holds for the RECORDING only (the corpus runner merges `env:` there and
nowhere else), so this trace is born the way every trace made before the
rule existed was born: plaintext at every one of the four sites -- `secret`,
`token`, the `authorization` map value, `send`'s argument. The one addition
over `secret_in_env`'s shape is `print(token)`, so the case can also show
the retrofit's honest limit: the content rule the retrofit runs cannot see
a `tok_corpus_...` value (no pattern matches it, B19), so the stored output
row still holds the token after the retrofit runs. No question in this case
may run a command that prints output rows for that reason.
"""
import os


def secret():
    return os.environ["SENSORIUM_CORPUS_TOKEN"]


def send(token):
    return None


def handle():
    token = secret()
    headers = {"authorization": token}
    send(token)
    print(token)
    return len(headers)


if __name__ == "__main__":
    handle()
