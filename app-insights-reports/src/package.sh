#!/usr/bin/env bash

set -e
cd $(dirname "$BASH_SOURCE")
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 PYTHON3_TAR_GZ"
    echo "Example: $0 ~/python/unravel-python-3.7.7-master.57.tar.gz"
    exit 1
fi
PYTHON3_TAR_GZ=$1

tmp=$(mktemp -d)
trap "rm -rf $tmp" EXIT

name=$(basename $PWD)
rm -rf $name.tar.gz
mkdir $tmp/$name
tar -xzf $PYTHON3_TAR_GZ -C $tmp/$name
cp -Lr . $tmp/$name/src
$tmp/$name/python3/bin/python -m pip install -r $tmp/$name/src/requirements.txt -t $tmp/$name/deps
tar -czf $name.tar.gz -C $tmp/ $name
echo $name.tar.gz created successfully
