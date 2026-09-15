import os


def secret():
    return os.environ["SENSORIUM_E16_TOKEN"]


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
