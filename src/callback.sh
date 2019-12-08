#!/bin/bash
cur_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null 2>&1 && pwd )"
patchfile_name="${cur_dir}/patch_file_$(date +%s)"

touch $patchfile_name

while IFS= read -r -d '' line; do
    printf '%s\0' "$line" >> "$patchfile_name"
done < <(cat $1)
printf "$line" >> "$patchfile_name"

python3 "${cur_dir}/callback.py" $patchfile_name
rm $patchfile_name
