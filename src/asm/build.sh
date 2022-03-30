# note: asm6f must be on the PATH.
configs=(NO_BOUNCY_LANDINGS NO_AUTO_SCROLL UNITILE EXTENDED_OBJECTS TEXT_DIACRITICS)
outs=(no-bouncy-landings no-auto-scroll unitile extended_objects diacritics)
folders=("no-bouncy-landings/" "no-auto-scroll/" "unitile/" "ext-objects/" "diacritics"/)

name="patches"

export="$name"

BASE=`find $(git rev-parse --show-toplevel) -iname "base.nes" | head -n 1`

if [ ! -f "build.sh" ]
then
    echo "must run this script from within the src/asm/ folder."
    exit 1
fi

if [ -d "$export" ]
then
    rm -r "$export"
fi
mkdir "$export"

if [ ! -d "nes" ]
then
    mkdir "nes"
fi

for i in {0..4}
do
    CONFIG="${configs[$i]}"
    SRC="patch.asm"
    TAG="${outs[$i]}"
    if [ $TAG != "standard" ]
    then
        OUT="$name-$TAG"
    else
        OUT="$name"
    fi
    folder="${folders[$i]}"
    
    if [ ! -f "$BASE" ]
    then
        echo "Base ROM $BASE not found -- skipping."
        continue
    fi
    
    echo
    echo "Producing hacks for $BASE"
    
    mkdir "$export/$folder"
        
    outfile="$OUT"
    
    echo "------------------------------------------"
    echo "generating patch ($outfile) from $BASE"
    chmod a-w "$BASE"
    echo "INCNES \"$BASE\"" > inc-base.asm
    which asm6f > /dev/null
    if [ $? != 0 ]
    then
        echo "asm6f is not on the PATH."
        continue
    fi
    printf 'base size 0x%x\n' `stat --printf="%s" "$BASE"`
    asm6f -c -n -i "-d$CONFIG" "-dUSEBASE" "$SRC" "$outfile.nes"
    
    if [ $? != 0 ]
    then
        exit
    fi
    
    printf 'out size 0x%x\n' `stat --printf="%s" "$outfile.nes"`
    
    if [ $? != 0 ]
    then
        exit 1
    fi
    
    #continue
    if ! [ -f "$outfile.ips" ]
    then
        echo
        echo "Failed to create $outfile.ips"
        exit 1
    fi
    echo

    # create python file
    if [ ! -d "../asmpy" ]
    then
        mkdir "../asmpy"
    fi

    python3 ./ips-to-python.py "$outfile.ips" "../asmpy/${outfile//-/_}.py"

    echo
    
    # apply ips patch
    chmod a+x flips/flips-linux
    
    if [ -f patch.nes ]
    then
      rm patch.nes
    fi
    
    flips/flips-linux --apply "$outfile.ips" "$BASE" patch.nes
    if ! [ -f "patch.nes" ]
    then
        echo "Failed to apply patch $i."
        exit 2
    fi
    echo "patch generated."
    md5sum "$outfile.nes"
    
    cmp "$outfile.nes" patch.nes
    if [ $? != 0 ]
    then
        exit 3
    fi
    
    mv -t nes/ $outfile.nes*
    
    if [ -f patch.nes ]
    then
      rm patch.nes
    fi
    
    mv $outfile.ips "$export/$folder/"
done

echo "============================================"
echo "Assembling export."

if [ -f $name.zip ]
then
  rm $name.zip 2>&1
fi
zip -r $name.zip $export/*