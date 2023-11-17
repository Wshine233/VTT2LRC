# ------ Configuration ------

# Output Folder, use "*" to use the same folder as the input file
output_folder = "*"

# Output File Name, use "/rREGEX/r" to use regex expression on the input file name(including original extension)
# if you want to use "/" in the regex, use "//" to escape it
# output_file_name = r"/r^.*?(?=(\.(wav|mp3|wmv|aac|flac|ape|aif|ogg))?\.vtt$)/r.lrc"
output_file_name = r"/r^.*?(?=(\.(wav|mp3|wmv|aac|flac|ape|aif|ogg))?\.vtt$)/r.lrc"

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

# Don't check the extension of the input file
check_extension = True

# If True, the script will convert all vtt files in the input folder recursively
recursion = True

# If True, the script will print the ignored files at the end of the process
log_ignored_files = False

# End of configuration

# ------ import ------
import re
from pathlib import Path
import os
import sys
import platform

# ------ status ------
has_error = False
ignore_list = []
parent_folder = Path()
version = "1.10"


def log_error(error: str):
    global has_error
    has_error = True
    print(f"[ERROR] {error}")
    print()


def add_ignore(path: Path, reason: str, log: bool):
    global ignore_list
    global parent_folder
    path = path.absolute()
    if path.is_relative_to(parent_folder):
        path = path.relative_to(parent_folder)

    ignore_list.append((path, reason))
    if log:
        log_error(f"{path.name} ignored: {reason}")


def print_ignore_list():
    global ignore_list
    global has_error
    has_error = True
    ignore_list.sort(key=lambda x: str(x[0]))
    print(f"------ Ignored Files ------")
    for path, reason in ignore_list:
        print(f"{path}: {reason}")
        print()
    print()


# ------ functions ------


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


def match_reg(reg, text):
    match = re.match(reg, text)
    if match:
        return match.group()
    else:
        return ""


def check_file_name(name: str) -> bool:
    # 简单检查文件名是否合法
    illegal_char = "/"
    os_name = platform.system()
    if os_name == "Windows":
        illegal_char = r"\/:*?\"<>|"
    elif os_name == "Linux":
        illegal_char = "/"
    elif os_name == "Darwin":
        illegal_char = ":"

    for c in illegal_char:
        if c in name:
            return False
    return True


def get_output_file_name(input_file_path: Path) -> str:
    file_name_origin = input_file_path.name
    text = ""
    pre_scan = False
    scan = False
    reg = ""
    for c in output_file_name:
        if c == "/" and pre_scan:
            # 转义成纯文本的/字符
            if scan:
                reg += c
            else:
                text += c
            pre_scan = False
        elif c == "/" and not pre_scan:
            pre_scan = True
        elif c == "r" and pre_scan:
            # /r代表正则表达式开始或结束
            scan = not scan
            if not scan:
                # 正则表达式结束
                text += match_reg(reg, file_name_origin)
                reg = ""
            pre_scan = False
        elif pre_scan:
            # 无效的转义动作，出现解析语法问题
            raise Exception(f"There's a SYNTAX ERROR in output_file_name configuration: {output_file_name}\n"
                            f"'/{c}' is not a valid escape action.")
        elif scan:
            # 正在扫描正则表达式
            reg += c
        else:
            text += c

    if scan:
        raise Exception(f"There's a SYNTAX ERROR in output_file_name configuration: {output_file_name}\n"
                        f"Regex escape '/r' not ended. (/rREGEX/r)")

    if not check_file_name(text):
        raise Exception(f"Output file name is illegal: {text}")

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
    lrc_text = f"[by:IceFoxy]\n[re:VTT to LRC]\n[ve:{version}]\n\n"
    for vtt in parse_vtt(vtt_text):
        lrc_text += f"[{vtt.time_start.to_lrc_str()}]{vtt.text}\n"
        if not ignore_end_time:
            lrc_text += f"[{vtt.time_end.to_lrc_str()}]\n"

    write_to_file(output_path, lrc_text)


def try_vtt2lrc(input_file_path: Path, log: bool):
    try:
        vtt2lrc(input_file_path)
    except Exception as e:
        add_ignore(input_file_path, f"Failed to convert: {e}", log)


def check_vtt(path: Path, log: bool) -> bool:
    if not path.exists():
        err_msg = f"File does not exist."
    elif path.is_dir():
        err_msg = f"File is a directory."
    elif check_extension and path.suffix != ".vtt":
        err_msg = f"Not a '.vtt' file."
    elif path.stat().st_size > 4 * 1024 * 1024:
        err_msg = f"Too large (>4MB)."
    else:
        return True

    add_ignore(path, err_msg, log)
    return False


def main_recursive(path_list: list[str]) -> int:
    if not check_extension:
        print(f"**Warning: check_extension is set to False, this will cause the script to try to process ALL FILES in "
              f"the folders.**")

    queue = list(map(lambda x: Path(x), path_list))
    file_cot = 0
    while len(queue) > 0:
        path = queue.pop()
        file_cot += 1
        if path.is_dir():
            # 扫描的文件夹不算入文件数
            file_cot -= 1
            for sub_path in path.iterdir():
                queue.append(sub_path)
        elif check_vtt(path, False):
            try_vtt2lrc(path, True)

    return file_cot


def main(args: list[str]) -> int:
    file_cot = 0
    for arg in args:
        file_cot += 1
        path = Path(arg)
        if check_vtt(path, True):
            try_vtt2lrc(path, True)
    return file_cot


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Please drag and drop the vtt file(s) to this script")
        input("Press Enter to exit")
        exit(0)

    file_count = 0
    try:
        parent_folder = Path(sys.argv[1]).parent.absolute()
        if recursion:
            file_count = main_recursive(sys.argv[1:])
        else:
            file_count = main(sys.argv[1:])
    except Exception as e:
        log_error(f"Unexpected error occurred: {e}")

    if len(ignore_list) > 0 and log_ignored_files:
        print_ignore_list()
    print("Done!")
    print(f"Total files: {file_count}  Ignored: {len(ignore_list)}")
    print()

    if has_error:
        input("Press Enter to exit")
