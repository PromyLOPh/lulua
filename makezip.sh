#!/bin/bash

tmpfile=$(mktemp -u)
in=$1
out=$2
pushd $(dirname $in) && zip -r $tmpfile $(basename $in) && popd && cp $tmpfile $out && rm $tmpfile

