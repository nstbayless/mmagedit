CPPARGS="-fPIC -static-libstdc++ -I/usr/include/python3.9/ -lpython3.9"
g++ -shared -o libmmagedit.so  mmagedit.cpp  $CPPARGS
g++ -o mmagedit  mmagedit.cpp  $CPPARGS -DMAIN