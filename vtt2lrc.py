# ------ Configuration ------

# Output Folder, use "*" to use the same folder as the input file
output_folder = "*"

# Output File Name, use "{regex}" to use regex expression on the input file name(including original extension)
# If you need to use "{" or "}" in the output file name, use "\" or "/" instead
output_file_name = r"{^.*?(?=(\.[0-9a-z]*)?\.vtt$)}.lrc"

# Output File Encoding
output_file_encoding = "utf-8"

# Input File Encoding
input_file_encoding = "utf-8"

# Ignore end time
# If not ignore, the lrc file will have a blank line after each line of lyrics

# 00:00:00.000 --> 00:01:00.000
# Lyrics
# ^ This will be converted to
# [00:00.00]Lyrics
# [00:01.00]
# ^ If ignore_end_time=True, the lrc file will not have the blank line
ignore_end_time = False

# If file name duplicate, should the script overwrite the file?
# If overwrite=False, the script will add "_" to the file name
overwrite = True

# End of configuration

# ------ import ------
import re
from pathlib import Path


# ------ functions ------

has_error = False


def get_output_folder(input_file_path: Path) -> Path:
    if output_folder == "*":
        return input_file_path.parent
    else:
        return Path(output_folder)


def get_non_duplicate_file_name(folder: Path, file_name: str) -> str:
    if overwrite:
        return file_name

    new_path = folder.joinpath(file_name)
    while new_path.exists():
        new_path = new_path.with_name(new_path.stem + "_" + new_path.suffix)
    return new_path.name


def get_output_file_name(input_file_path: Path) -> str:
    file_name_origin = input_file_path.name
    text = ""
    scan = False
    reg = ""
    for c in output_file_name:
        if c == "{":
            scan = True
        elif c == "}":
            scan = False
            match = re.match(reg, file_name_origin)
            if match:
                text += match.group()
        elif scan:
            reg += c
        elif c == "\\":
            text += "{"
        elif c == "/":
            text += "}"
        else:
            text += c

    text = get_non_duplicate_file_name(get_output_folder(input_file_path), text)
    return text


def write_to_file(output_file_path: Path, output_text: str):
    if overwrite:
        output_file_path.unlink(missing_ok=True)
    with open(output_file_path, "x", encoding=output_file_encoding) as output_file:
        output_file.write(output_text)


def read_vtt(input_file_path: Path) -> str:
    with open(input_file_path, "r", encoding=input_file_encoding) as input_file:
        return input_file.read()


class Time:
    hour: int
    minute: int
    second: int
    millisecond: int

    def __init__(self, hour: int, minute: int, second: int, millisecond: int):
        self.hour = hour
        self.minute = minute
        self.second = second
        self.millisecond = millisecond

    def __str__(self):
        return f"{self.hour}:{self.minute}:{self.second}.{self.millisecond}"

    def to_lrc_str(self):
        return f"{self.minute + self.hour * 60:0>2d}:{self.second:0>2d}.{self.millisecond // 10:0>2d}"


def parse_time(time_str: str) -> Time:
    time_str = time_str.strip()
    hour = int(time_str[0:time_str.find(":")])
    time_str = time_str[time_str.find(":") + 1:]
    minute = int(time_str[0:time_str.find(":")])
    time_str = time_str[time_str.find(":") + 1:]
    second = int(time_str[0:time_str.find(".")])
    time_str = time_str[time_str.find(".") + 1:]
    millisecond = int(time_str)
    return Time(hour, minute, second, millisecond)


class VTT:
    time_start: Time
    time_end: Time
    text: str

    def __init__(self, time_start: str, time_end: str, text: str):
        self.time_start = parse_time(time_start)
        self.time_end = parse_time(time_end)
        self.text = text


def log_error(error: str):
    global has_error
    has_error = True
    print(f"[ERROR] {error}")
    print()


def parse_vtt(vtt_text: str) -> list[VTT]:
    vtt_list = []
    vtt_obj = None
    for line in vtt_text.split("\n"):
        if line.strip() == "":
            continue
        if line.strip() != "WEBVTT":
            return []
        else:
            break

    for line in vtt_text.split("\n"):
        if vtt_obj is not None:
            if line.strip() == "":
                vtt_list.append(vtt_obj)
                vtt_obj = None
            else:
                vtt_obj.text += line.strip() + " "
        elif line.find("-->") != -1:
            time_start = line[0:line.find("-->")].strip()
            time_end = line[line.find("-->") + 3:].strip()
            vtt_obj = VTT(time_start, time_end, "")

    if vtt_obj is not None:
        vtt_list.append(vtt_obj)

    return vtt_list


# ------ main ------

def vtt2lrc(input_file_path: Path):
    output_name = get_output_file_name(input_file_path)
    output_path = get_output_folder(input_file_path).joinpath(output_name)

    vtt_text = read_vtt(input_file_path)
    lrc_text = "[by:IceFoxy]\n[re:VTT to LRC]\n[ve:1.00]\n\n"
    for vtt in parse_vtt(vtt_text):
        lrc_text += f"[{vtt.time_start.to_lrc_str()}]{vtt.text}\n"
        if not ignore_end_time:
            lrc_text += f"[{vtt.time_end.to_lrc_str()}]\n"

    write_to_file(output_path, lrc_text)


def main(args):
    if len(args) == 0:
        print("Please drag and drop the vtt file(s) to this script")
        input("Press Enter to exit")
        return

    for arg in args:
        path = Path(arg)
        if not path.exists():
            log_error(f"{path.name} does not exist, ignored.")
        elif path.is_dir():
            log_error(f"{path.name} is a directory, ignored.")
        elif path.stat().st_size > 4 * 1024 * 1024:
            log_error(f"{path.name} is too large (>4MB), ignored.")
        elif path.suffix != ".vtt":
            log_error(f"{path.name} is not a vtt file, ignored.\nIf it is, please rename it to {path.name}.vtt")
        else:
            try:
                vtt2lrc(Path(arg))
            except Exception as e:
                log_error(f"{path.name} failed to convert, ignored.\n{e}")


if __name__ == '__main__':
    import sys

    main(sys.argv[1:])
    if has_error:
        input("Press Enter to exit")

