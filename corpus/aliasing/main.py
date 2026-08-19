"""Seeded bug: derive_sandbox does not copy the config it was handed, so
`sandbox["timeout"] = 1` writes through to the production dict. The program
prints the production timeout and it is 1."""


def make_default():
    return {"retries": 3, "timeout": 30}


def derive_sandbox(cfg):
    sandbox = cfg                 # BUG: alias, not a copy
    sandbox["timeout"] = 1
    return sandbox


def main():
    prod = make_default()
    sand = derive_sandbox(prod)
    print("prod timeout:", prod["timeout"], "sandbox timeout:",
          sand["timeout"])


if __name__ == "__main__":
    main()
