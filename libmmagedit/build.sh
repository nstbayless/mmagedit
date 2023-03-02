CPPARGS="-fPIC -static-libstdc++ -I/usr/include/python3.9/ -lpython3.9 -std=c++11"

set -e
echo "building..."

g++ -static-libstdc++ -shared -o libmmagedit.so  mmagedit.cpp  $CPPARGS
g++ -static-libstdc++ -o mmagedit  mmagedit.cpp  $CPPARGS -DMAIN -g -DLOCAL_PYTHON_H

if command -v patchelf > /dev/null
then
    patchelf --set-rpath "\$ORIGIN" libmmagedit.so
    patchelf --set-rpath "\$ORIGIN:\$ORIGIN/lib" mmagedit
else
    echo "please install patchelf to add \$ORIGIN to libmmagedit RPATH"
fi

echo "build complete."