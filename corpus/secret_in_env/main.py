"""Not a seeded bug: this case demonstrates rule v1's NAME rule, not a
defect. Every binding that touches the planted token is named to fire it --
`secret`, `token`, `authorization`, `send` is the one name that does not, and
it never holds the value itself. No `print` here (B19): the point is that
the trace never holds the token, and printing it would be the same leak the
rule exists to stop, staged inside the very case meant to demonstrate it.
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
    return len(headers)


if __name__ == "__main__":
    handle()
