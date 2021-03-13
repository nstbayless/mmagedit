CPPARGS="-fPIC -static-libstdc++ -I/usr/include/python3.9/ -lpython3.9"

set -e
echo "building..."

g++ -shared -o libmmagedit.so  mmagedit.cpp  $CPPARGS
g++ -o mmagedit  mmagedit.cpp  $CPPARGS -DMAIN

if command -v patchelf > /dev/null
then
    patchelf --set-rpath "\$ORIGIN" libmmagedit.so
    patchelf --set-rpath "\$ORIGIN" mmagedit
else
    echo "please install patchelf to add \$ORIGIN to libmmagedit RPATH"
fi

echo "build complete."