import tomli

def pause():
    programPause = input("Press the <ENTER> key to continue...")

def read_toml_file(filename):
  with open(filename, "rb") as f:
    toml_dict = tomli.load(f)
    return toml_dict
