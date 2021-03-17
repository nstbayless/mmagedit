// replacement for python.h library headers

#include "stdio.h"

#if defined(_WIN32) || defined(__CYGWIN__)
    #define Py_IMPORTED_SYMBOL __declspec(dllimport)
    #define Py_EXPORTED_SYMBOL __declspec(dllexport)
    #define Py_LOCAL_SYMBOL
#else
/*
 * If we only ever used gcc >= 5, we could use __has_attribute(visibility)
 * as a cross-platform way to determine if visibility is supported. However,
 * we may still need to support gcc >= 4, as some Ubuntu LTS and Centos versions
 * have 4 < gcc < 5.
 */
    #ifndef __has_attribute
      #define __has_attribute(x) 0  // Compatibility with non-clang compilers.
    #endif
    #if (defined(__GNUC__) && (__GNUC__ >= 4)) ||\
        (defined(__clang__) && __has_attribute(visibility))
        #define Py_IMPORTED_SYMBOL __attribute__ ((visibility ("default")))
        #define Py_EXPORTED_SYMBOL __attribute__ ((visibility ("default")))
        #define Py_LOCAL_SYMBOL  __attribute__ ((visibility ("hidden")))
    #else
        #define Py_IMPORTED_SYMBOL
        #define Py_EXPORTED_SYMBOL
        #define Py_LOCAL_SYMBOL
    #endif
#endif

/* If no external linkage macros defined by now, create defaults */
#ifndef PyAPI_FUNC
#       define PyAPI_FUNC(RTYPE) Py_EXPORTED_SYMBOL RTYPE
#endif
#ifndef PyAPI_DATA
#       define PyAPI_DATA(RTYPE) extern Py_EXPORTED_SYMBOL RTYPE
#endif
#ifndef PyMODINIT_FUNC
#       if defined(__cplusplus)
#               define PyMODINIT_FUNC extern "C" Py_EXPORTED_SYMBOL PyObject*
#       else /* __cplusplus */
#               define PyMODINIT_FUNC Py_EXPORTED_SYMBOL PyObject*
#       endif /* __cplusplus */
#endif

// function declarations
typedef ssize_t         Py_ssize_t;

typedef struct _object {
    Py_ssize_t ob_refcnt;
    void *ob_type;
} PyObject;


/* Similar to PyUnicode_FromUnicode(), but u points to UTF-8 encoded bytes */
PyAPI_FUNC(PyObject*) PyUnicode_FromStringAndSize(
    const char *u,             /* UTF-8 encoded string */
    Py_ssize_t size            /* size of buffer */
    );

/* Similar to PyUnicode_FromUnicode(), but u points to null-terminated
   UTF-8 encoded bytes.  The size is determined with strlen(). */
PyAPI_FUNC(PyObject*) PyUnicode_FromString(
    const char *u              /* UTF-8 encoded string */
    );

PyAPI_FUNC(PyObject *) PyObject_CallMethodObjArgs(
    PyObject *obj,
    PyObject *name,
    ...);

PyAPI_FUNC(PyObject*) PyUnicode_AsEncodedString(
    PyObject *unicode,          /* Unicode object */
    const char *encoding,       /* encoding */
    const char *errors          /* error handling */
    );

PyAPI_FUNC(char *) PyBytes_AsString(PyObject *);

#define PyBytes_AS_STRING PyBytes_AsString

PyAPI_FUNC(PyObject *) PyObject_Repr(PyObject *);
PyAPI_FUNC(PyObject *) PyObject_Str(PyObject *);

PyAPI_FUNC(PyObject *) PyErr_Occurred(void);
PyAPI_FUNC(void) PyErr_Clear(void);
PyAPI_FUNC(void) PyErr_Fetch(PyObject **, PyObject **, PyObject **);
PyAPI_FUNC(void) PyErr_Restore(PyObject *, PyObject *, PyObject *);

PyAPI_FUNC(void) PyErr_GetExcInfo(PyObject **, PyObject **, PyObject **);
PyAPI_FUNC(void) PyErr_SetExcInfo(PyObject *, PyObject *, PyObject *);

PyAPI_FUNC(void) PyErr_NormalizeException(PyObject**, PyObject**, PyObject**);

PyAPI_FUNC(PyObject *) PyObject_GetAttrString(PyObject *, const char *);
PyAPI_FUNC(int) PyObject_SetAttrString(PyObject *, const char *, PyObject *);
PyAPI_FUNC(int) PyObject_HasAttrString(PyObject *, const char *);
PyAPI_FUNC(PyObject *) PyObject_GetAttr(PyObject *, PyObject *);
PyAPI_FUNC(int) PyObject_SetAttr(PyObject *, PyObject *, PyObject *);
PyAPI_FUNC(int) PyObject_HasAttr(PyObject *, PyObject *);

PyAPI_FUNC(PyObject *) PyList_New(Py_ssize_t size);
PyAPI_FUNC(Py_ssize_t) PyList_Size(PyObject *);

PyAPI_FUNC(PyObject *) PyList_GetItem(PyObject *, Py_ssize_t);
PyAPI_FUNC(int) PyList_SetItem(PyObject *, Py_ssize_t, PyObject *);
PyAPI_FUNC(int) PyList_Insert(PyObject *, Py_ssize_t, PyObject *);
PyAPI_FUNC(int) PyList_Append(PyObject *, PyObject *);

PyAPI_FUNC(PyObject *) PyList_GetSlice(PyObject *, Py_ssize_t, Py_ssize_t);
PyAPI_FUNC(int) PyList_SetSlice(PyObject *, Py_ssize_t, Py_ssize_t, PyObject *);

PyAPI_FUNC(int) PyList_Sort(PyObject *);
PyAPI_FUNC(int) PyList_Reverse(PyObject *);
PyAPI_FUNC(PyObject *) PyList_AsTuple(PyObject *);

/* Initialization and finalization */
PyAPI_FUNC(void) Py_Initialize(void);
PyAPI_FUNC(void) Py_InitializeEx(int);
PyAPI_FUNC(void) Py_Finalize(void);
PyAPI_FUNC(int) Py_FinalizeEx(void);
PyAPI_FUNC(int) Py_IsInitialized(void);

PyAPI_FUNC(PyObject *) PyDict_New(void);
PyAPI_FUNC(PyObject *) PyDict_GetItem(PyObject *mp, PyObject *key);
PyAPI_FUNC(PyObject *) PyDict_GetItemWithError(PyObject *mp, PyObject *key);
PyAPI_FUNC(int) PyDict_SetItem(PyObject *mp, PyObject *key, PyObject *item);
PyAPI_FUNC(int) PyDict_DelItem(PyObject *mp, PyObject *key);
PyAPI_FUNC(void) PyDict_Clear(PyObject *mp);
PyAPI_FUNC(int) PyDict_Next(
    PyObject *mp, Py_ssize_t *pos, PyObject **key, PyObject **value);
PyAPI_FUNC(PyObject *) PyDict_Keys(PyObject *mp);
PyAPI_FUNC(PyObject *) PyDict_Values(PyObject *mp);
PyAPI_FUNC(PyObject *) PyDict_Items(PyObject *mp);
PyAPI_FUNC(Py_ssize_t) PyDict_Size(PyObject *mp);
PyAPI_FUNC(PyObject *) PyDict_Copy(PyObject *mp);
PyAPI_FUNC(int) PyDict_Contains(PyObject *mp, PyObject *key);


PyAPI_FUNC(wchar_t *) Py_DecodeLocale(
    const char *arg,
    size_t *size);

PyAPI_FUNC(char*) Py_EncodeLocale(
    const wchar_t *text,
    size_t *error_pos);

PyAPI_FUNC(char*) _Py_EncodeLocaleRaw(
    const wchar_t *text,
    size_t *error_pos);


PyAPI_FUNC(void *) PyMem_RawMalloc(size_t size);
PyAPI_FUNC(void *) PyMem_RawCalloc(size_t nelem, size_t elsize);
PyAPI_FUNC(void *) PyMem_RawRealloc(void *ptr, size_t new_size);
PyAPI_FUNC(void) PyMem_RawFree(void *ptr);


PyAPI_FUNC(void) PySys_SetArgv(int, wchar_t **);
PyAPI_FUNC(void) PySys_SetArgvEx(int, wchar_t **, int);
PyAPI_FUNC(void) PySys_SetPath(const wchar_t *);

PyAPI_FUNC(PyObject *) PyImport_ImportModule(
    const char *name            /* UTF-8 encoded string */
    );

PyAPI_FUNC(void) PyErr_Print(void);
PyAPI_FUNC(void) PyErr_PrintEx(int);
PyAPI_FUNC(void) PyErr_Display(PyObject *, PyObject *, PyObject *);


PyAPI_FUNC(PyObject *) PyDict_GetItemString(PyObject *dp, const char *key);
PyAPI_FUNC(int) PyDict_SetItemString(PyObject *dp, const char *key, PyObject *item);
PyAPI_FUNC(int) PyDict_DelItemString(PyObject *dp, const char *key);

PyAPI_FUNC(PyObject *) PyTuple_New(Py_ssize_t size);
PyAPI_FUNC(Py_ssize_t) PyTuple_Size(PyObject *);
PyAPI_FUNC(PyObject *) PyTuple_GetItem(PyObject *, Py_ssize_t);
PyAPI_FUNC(int) PyTuple_SetItem(PyObject *, Py_ssize_t, PyObject *);
PyAPI_FUNC(PyObject *) PyTuple_GetSlice(PyObject *, Py_ssize_t, Py_ssize_t);
PyAPI_FUNC(PyObject *) PyTuple_Pack(Py_ssize_t, ...);

PyAPI_FUNC(PyObject *) PyObject_Call(PyObject *callable,
                                     PyObject *args, PyObject *kwargs);

PyAPI_FUNC(Py_ssize_t) PyNumber_AsSsize_t(PyObject *o, PyObject *exc);
PyAPI_FUNC(PyObject *) PyBool_FromLong(long);
PyAPI_FUNC(int) PyObject_IsTrue(PyObject *);
PyAPI_FUNC(int) PyObject_Not(PyObject *);


PyAPI_FUNC(PyObject *) PyLong_FromLong(long);
PyAPI_FUNC(PyObject *) PyLong_FromUnsignedLong(unsigned long);
PyAPI_FUNC(PyObject *) PyLong_FromSize_t(size_t);
PyAPI_FUNC(PyObject *) PyLong_FromSsize_t(Py_ssize_t);
PyAPI_FUNC(PyObject *) PyLong_FromDouble(double);
PyAPI_FUNC(long) PyLong_AsLong(PyObject *);

#define _PyObject_CAST(op) ((PyObject*)(op))

#define Py_DECREF(op) _Py_DECREF(_PyObject_CAST(op))

PyAPI_FUNC(void) _Py_Dealloc(PyObject *);


static inline void _Py_DECREF(
    PyObject *op)
{
    if (--op->ob_refcnt != 0) {

    }
    else {
        _Py_Dealloc(op);
    }
}


static inline void _Py_XDECREF(PyObject *op)
{
    if (op != NULL) {
        Py_DECREF(op);
    }
}

#define Py_XDECREF(op) _Py_XDECREF(_PyObject_CAST(op))
