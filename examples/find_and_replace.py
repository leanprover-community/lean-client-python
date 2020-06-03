#!/usr/bin/env python
from pathlib import Path

import trio # type: ignore
from lean_client.commands import InfoRequest, InfoResponse

from lean_client.trio_server import TrioLeanServer

# terminal decorations
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


async def main(path, full_id_old, full_id_new):
    old_parts = full_id_old.split(".")
    new_parts = full_id_new.split(".")
    assert old_parts[:-1] == new_parts[:-1], \
        f"{full_id_old} and {full_id_new} have to be the same except for the final part after the '.'"

    old_word = old_parts[-1]
    new_word = new_parts[-1]

    # find all instances of old_word

    files = sorted(Path(path).glob('**/*.lean'))  # recursive
    file_instances = []
    total_count = 0
    for f in files:
        lines = f.read_text().split('\n')

        line_instances = []
        for i, line in enumerate(lines):
            pos_instances = []
            for j, _ in enumerate(line):
                j_end = j + len(old_word)
                if line[j:j_end] == old_word:
                    # check that word doesn't continue
                    if j == 0 or line[j-1].isalpha() or line[j] == "_":
                        continue
                    if j_end != len(line) and (j_end > len(line) or line[j_end].isalnum() or line[j_end] == "_" or line[j_end] == "'"):
                        continue
                    pos_instances.append((j, j_end))
                    total_count += 1

            if pos_instances:
                line_instances.append((i, line, pos_instances))

        if line_instances:
            file_instances.append((f, line_instances))

    print(f'Found {total_count} occurrences of the word "{old_word}" in {len(file_instances)} Lean files.')
    print()

    if not total_count:
        return

    print(f'Checking which ones are instances of "{full_id_old}".  This will take a while.')
    print()

    async with trio.open_nursery() as nursery:
        file_instances2 = []
        total_count2 = 0
        for f, line_instances in file_instances:
            print()
            print(f"Checking {str(f)}")

            # Start and kill server for each file to avoid memory blowup.
            # Doesn't have a significant impact on overall time.
            server = TrioLeanServer(nursery, lean_cmd="lean")
            await server.start()
            await server.full_sync(str(f))

            line_instances2 = []
            for i, line, pos_instances in line_instances:
                pos_instances2 = []
                for j, j_end in pos_instances:
                    resp = await server.send(InfoRequest(str(f), i+1, j))  # i+1 since lean 1-indexes lines

                    if isinstance(resp, InfoResponse) and resp.record.full_id == full_id_old:
                        pos_instances2.append((j, j_end))
                        total_count2 += 1

                if pos_instances2:
                    print(f'Line {i+1:4}: {line}')
                    underline = ""
                    for j, j_end in pos_instances2:
                        underline += " " * (j - len(underline))
                        underline += "^" * (j_end - j)
                    print(f"           {underline}")

                    line_instances2.append((i, line, pos_instances2))

            if line_instances2:
                file_instances2.append((f, line_instances2))

            server.process.kill()

        nursery.cancel_scope.cancel()

    print()
    print(f'Found {total_count2} instances of "{full_id_old}" in {len(file_instances2)} files.')
    while True:
        answer = input(f'Do you want to change those {total_count2} occurrences of "{old_word}" to "{new_word}"? [y/n] : ')
        answer = answer.lower().strip()
        if answer in ["n", "no"]:
            print("Aborted.")
            return
        elif answer in ["y", "yes"]:
            break

    print()

    # change occurrences
    for f, line_instances2 in file_instances2:
        print(f"Changing {str(f)}")

        new_line_dict = {}
        for i, line, pos_instances2 in line_instances2:
            new_line = ""
            pos = 0
            for j, j_end in pos_instances2:
                new_line += line[pos:j]
                new_line += new_word
                pos = j_end
            new_line += line[pos:]

            new_line_dict[i] = new_line

        old_lines = f.read_text().split('\n')
        new_lines = []
        for i, line in enumerate(old_lines):
            if i in new_line_dict:
                new_lines.append(new_line_dict[i])
            else:
                new_lines.append(line)

        f.write_text("\n".join(new_lines))

    print()
    print("Done.")

if __name__ == '__main__':
    path = 'find_and_replace/'
    old, new = "stack.head", "stack.peek"
    trio.run(main, path, old, new)
