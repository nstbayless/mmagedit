#include "mmagedit.h"
#include "defer.h"

#include <type_traits>
#include <cstdint>
#include <cstdlib>
#include <iostream>

#ifdef LOCAL_PYTHON_H
	#include "py.h"
#else
	#include <Python.h>
#endif

#include <deque>

typedef PyObject PyObjectBorrowed;

#define defer_decref(pyobj) defer(Py_XDECREF(pyobj))
#define store_string(s) (g_static_string_out = s).c_str()

#define check_not_null(param) if (!param) return error("received nullptr string paramter (" #param ")")
#define check_not_null_rv(param, rv) if (!param) return error("received nullptr string paramter (" #param ")", rv)

#define args_end nullptr

#define min_version 202103181058

namespace
{
	int g_log_level = 0;
	size_t g_logc = 100;
	std::deque<std::pair<std::string, int>> g_logs;
	bool g_log_stdout = true;

	void crop_logs()
	{
		if (g_logc && g_logs.size() > g_logc)
		{
			// removes ending elements to fit to reduced size.
			g_logs.resize(g_logc);
		}
	}

	template<typename T>
	void log(T val, int level = LOG_TRIVIAL)
	{
		if (level <= g_log_level)
		{
			// add to logs list
			g_logs.emplace_front(val, level);
			crop_logs();

			// tee to stdout
			if (g_log_stdout)
			{
				(level == LOG_ERROR ? std::cerr : std::cout)
					<< val << std::endl;
			}
		}
	}

	PyObject* PyString(const char* s)
	{
		return PyUnicode_FromString(s);
	}

	template<typename... T>
	decltype(PyObject_CallMethodObjArgs(nullptr, nullptr))
	PyObject_CallMethodObjArgsString(
		PyObject* obj,
		const char* attr,
		T... args
	)
	{
		PyObject* attrstr = PyString(attr);
		defer_decref(attrstr);

		return PyObject_CallMethodObjArgs(obj, attrstr, args...);
	}

	std::string PyObject_AsString(PyObjectBorrowed* po)
	{
		if (po)
		{
			if (PyUnicode_Check(po))
			{
				PyObject* str = PyUnicode_AsEncodedString(po, "utf-8", "~E~");
				defer_decref(str);
				const char *bytes = PyBytes_AS_STRING(str);

				return bytes;
			}
			else
			{
				PyObject* repr = PyObject_Repr(po);
				defer_decref(repr);
				PyObject* str = PyUnicode_AsEncodedString(repr, "utf-8", "~E~");
				defer_decref(str);
				const char *bytes = PyBytes_AS_STRING(str);

				return bytes;
			}
		}
		else
		{
			return "null";
		}
	}

	std::string _dirname(std::string path)
	{
		size_t index_of_backslash = path.rfind("\\");
		size_t index_of_slash = path.rfind("/");
		size_t index_of_pathsep;
		if (index_of_backslash != std::string::npos && index_of_slash != std::string::npos)
		{
			if (index_of_backslash > index_of_slash)
			{
				index_of_pathsep = index_of_backslash;
			}
			else
			{
				index_of_pathsep = index_of_slash;
			}
		}
		else if (index_of_backslash != std::string::npos)
		{
			index_of_pathsep = index_of_backslash;
		}
		else if (index_of_slash != std::string::npos)
		{
			index_of_pathsep = index_of_slash;
		}
		else
		{
			return "./";
		}

		return path.substr(0, index_of_pathsep + 1);
	}

	// traceback module
	PyObject* g_traceback;

	// used to hold string references that are
	// returned by library functions.
	std::string g_static_string_out;

	std::string g_error = "";

	template <typename S=const char*, typename T=error_code_t>
	inline T error(S _error, T code)
	{
		g_error = _error;

		log("mmdata error: " + std::string(_error), LOG_ERROR);

		return code;
	}

	template <typename S=const char*, typename T=error_code_t>
	inline T error(S _error)
	{
		return error(_error, 1);
	}

	// return an error code if python has thrown an exception.
	#define check_error_python(errcode) \
		 if (check_error_python_impl()) return errcode;

	// check in advance of running a function if the python error is already triggered, and if so,
	// report that.
	#define precheck_error_python(errcode) \
		if (check_error_python_impl("A python error has occurred before entering the libmagedit function. This is an internal library error and should be reported to the developer.")) return errcode;

	#define postcheck_error_python(errcode) \
		if (check_error_python_impl("A python error has occurred before the libmagedit function exited. This is an internal library error and should be reported to the developer.")) return errcode;

	inline int check_error_python_impl(std::string message_prelude="")
	{
		PyObject* ptype = nullptr;
		PyObject* pvalue = nullptr;
		PyObject* pbt = nullptr;

		if (PyErr_Occurred())
		{
			PyErr_Fetch(&ptype, &pvalue, &pbt);
			// an error has occurred
			std::string s;
			s = message_prelude + "A python exception occurred.";
			
			if (g_traceback)
			{
				PyErr_NormalizeException(&ptype, &pvalue, &pbt);
				PyErr_SetExcInfo(ptype, pvalue, pbt);
				PyObject* exc_str = PyObject_CallMethodObjArgsString(g_traceback, "format_exc", args_end);
				defer_decref(exc_str);
				if (exc_str)
				{
					s += "\n" + PyObject_AsString(exc_str);
				}
				else
				{
					s += " (unable to decode exception details)";
				}
			}
			else
			{
				Py_XDECREF(ptype);
				Py_XDECREF(pvalue);
				Py_XDECREF(pbt);
			}

			PyErr_Clear();

			return error(s);
		}

		return 0;
	}

	PyObject *g_globals, *g_locals;

	// mmagedit modules
	PyObjectBorrowed *g_constants, *g_util;

	// MMData instance
	PyObject* g_data;

	PyObjectBorrowed* get_world(world_idx_t idx)
	{
		if (idx < 0) return nullptr;
		PyObjectBorrowed* world_array = PyObject_GetAttrString(g_data, "worlds");
		if (!world_array)
		{
			return nullptr;
		}

		if (idx < PyList_Size(world_array))
		{
			return PyList_GetItem(world_array, idx);
		}

		return nullptr;
	}
}

int
mmagedit_get_error_occurred()
{
	return g_error.length() > 0;
}

void mmagedit_clear_error()
{
	g_error = "";
}

const char*
mmagedit_get_error()
{
	defer(mmagedit_clear_error());
	return store_string(g_error);
}

void mmagedit_set_log_level(int l)
{
	g_log_level = l;
}


void
mmagedit_set_log_stdout(int v)
{
	g_log_stdout = !!v;
}

void
mmagedit_set_log_count_max(int c)
{
	if (c >= 0)
	{
		g_logc = c;
		crop_logs();
	}
}

int
mmagedit_get_log_count(int c)
{
	return g_logs.size();
}

const char*
mmagedit_get_log_entry(int n)
{
	if (n >= 0 && n < g_logs.size())
	{
		return store_string(g_logs.at(n).first);
	}
	return "";
}

int
mmagedit_get_log_entry_level(int n)
{
	if (n >= 0 && n < g_logs.size())
	{
		return g_logs.at(n).second;
	}
	return -1;
}

int mmagedit_init(const char* path_to_mmagedit)
{
	check_not_null(path_to_mmagedit);

	log("initializing libpython...");
	Py_Initialize();
	log("done.");

	g_globals = PyDict_New();
	g_locals = PyDict_New();

	{
		// set arg0 to path to mmagedit.py
		// set arg1 to "--as-lib"
		wchar_t* args[2] {
			Py_DecodeLocale(path_to_mmagedit, nullptr),
			Py_DecodeLocale("--as-lib", nullptr)
		};
		defer(PyMem_RawFree(args[0]));
		defer(PyMem_RawFree(args[1]));
		PySys_SetArgv(2, args);
	}

	if (!g_globals || !g_locals)
	{
		return error("Unable to create globals/locals dicts");
	}

	g_traceback = PyImport_ImportModule("traceback");
	check_error_python(-1);
	if (!g_traceback) return error("unable to access traceback module.");

	// get path list
	{
		log("updating sys.path...");
		PyObject* run_rv = PyRun_String(
			"import sys\n"
			"import os\n"
			"if len(sys.path) > 0:\n"
			"  if not os.path.exists(os.path.join(sys.path[0], \"src\")):\n"
			"    sys.path[0] = os.path.join(sys.path[0], \"mmagedit\")\n"
			,
			Py_file_input,
			g_globals, g_locals
		);
		defer_decref(run_rv);
		log("sys.path is: " + PyObject_AsString(
			PyObject_GetAttrString(
            	PyDict_GetItemString(g_locals, "sys"),
				"path"
			)
        ), LOG_INFO);
	}

	// run mmagedit.py	
	log("loading mmagedit...");
	PyObject* run_rv = PyRun_String(
		"from src import constants\n"
		"from src import util\n"
		"from src.mmdata import MMData\n",
		Py_file_input,
		g_globals, g_locals
	);
	log("done.");
	defer_decref(run_rv);
	check_error_python(-1);

	if (!run_rv)
	{
		PyErr_Print();
		return error("A python exception occurred while loading mmagedit.");
	}

	// retrieve important locals
	g_constants = PyDict_GetItemString(g_locals, "constants");
	g_util = PyDict_GetItemString(g_locals, "util");

	if (!g_constants || !g_util) return error("unable to access src.constants or src.util modules");

	// create mmdata instance
	PyObjectBorrowed* MMData = PyDict_GetItemString(g_locals, "MMData");
	if (!MMData) return error("unable to access class src.mmdata.MMData");

	PyObject* args = PyTuple_New(0);
	defer_decref(args);

	g_data = PyObject_Call(MMData, args, nullptr);
	check_error_python(-1);
	if (!g_data) return error("unable to create MMData instance");

	// set mmdata to local
	if (PyDict_SetItemString(g_locals, "mmdata", g_data))
	{
		return error("Unable to set local variable mmdata");
	}

	auto version = mmagedit_get_version_int();
	if (version < min_version)
	{
		return error("libmmagedit requires a more recent version of the library. (format " + std::to_string(version) + " is installed, but libmmagedit needs at least format " + std::to_string(min_version) + ")");
	}

	postcheck_error_python(1);
	return 0;
}

int
mmagedit_run_pystring(const char* str, int start)
{
	check_not_null(str);
	precheck_error_python(1);

	if (start == 0) start = Py_file_input;
	PyObject* run_rv = PyRun_String(
		str,
		start,
		g_globals, g_locals
	);
	defer_decref(run_rv);
	check_error_python(-1);
	return !run_rv;
}

int
mmagedit_get_python_int(int local, const char* variable_name)
{
	check_not_null(variable_name);
	precheck_error_python(0);

	PyObjectBorrowed* v = PyDict_GetItemString(
		local ? g_locals : g_globals,
		variable_name
	);

	check_error_python(0);

	int o = PyNumber_AsSsize_t(v, nullptr);

	check_error_python(0);

	return o;
}

const char*
mmagedit_get_python_str(int local, const char* variable_name)
{
	check_not_null_rv(variable_name, "");
	precheck_error_python("");

	PyObjectBorrowed* v = PyDict_GetItemString(
		local ? g_locals : g_globals,
		variable_name
	);

	check_error_python("");

	std::string o = PyObject_AsString(v);

	check_error_python("");

	return store_string(o);
}

int mmagedit_end()
{
	Py_XDECREF(g_globals);
	Py_XDECREF(g_locals);
	Py_XDECREF(g_data);

	Py_Finalize();

	return 0;
}

const char*
mmagedit_get_name_version_date()
{
	precheck_error_python("");

	PyObjectBorrowed* fn = PyObject_GetAttrString(g_constants, "get_version_and_date");

	PyObject* args = PyTuple_New(0);
	defer_decref(args);

	PyObject* result = PyObject_Call(fn, args, nullptr);
	check_error_python("");
	defer_decref(result);

	return store_string(PyObject_AsString(result));
}

uint64_t
mmagedit_get_version_int()
{
	precheck_error_python(0);

	PyObjectBorrowed* pob = PyObject_GetAttrString(g_constants, "mmfmt");

	PyObject* p32 = PyLong_FromLong(28);
	defer_decref(p32);

	PyObject* rsh = PyNumber_Rshift(pob, p32);
	defer_decref(rsh);

	uint64_t a = PyNumber_AsSsize_t(
		pob,
		nullptr
	) % (1 << 28);

	uint64_t b = PyNumber_AsSsize_t(
		rsh,
		nullptr
	);

	return (a | (b << 28));
}

uint64_t
mmagedit_get_minimum_version_int()
{
	return min_version;
}

// returns 1 andsets error to mmdata's errors if any occurred;
// otherwise, returns 0.
#define check_error_mmdata if (error_code_t e = _check_error_mmdata_impl()) return e;
#define check_error_mmdata_rval(rval) if (error_code_t e = [](){check_error_mmdata else return 0;}()) return rval;
static error_code_t _check_error_mmdata_impl()
{
	PyObject* result = PyObject_CallMethodObjArgsString(g_data, "errors_string", args_end);
	check_error_python(1);
	defer_decref(result);

	if (result && result != Py_None)
	{
		return error(PyObject_AsString(result));
	}

	return 0;
}

error_code_t
mmagedit_load_rom(const char* path_to_rom)
{
	precheck_error_python(1);
	check_not_null(path_to_rom);

	PyObject* rompath = PyString(path_to_rom);
	defer_decref(rompath);

	PyObject* result = PyObject_CallMethodObjArgsString(g_data, "read", rompath, args_end);
	check_error_python(1);
	defer_decref(result);

	if (!result) return error("failure to invoke mmdata.read()");

	if (PyObject_Not(result))
	{
		check_error_mmdata else return error("unknown error");
	}

	return 0;
}

error_code_t
mmagedit_load_hack(const char* path_to_hack)
{
	precheck_error_python(1);
	check_not_null(path_to_hack);

	PyObject* hackpath = PyString(path_to_hack);
	defer_decref(hackpath);

	PyObject* result = PyObject_CallMethodObjArgsString(g_data, "parse", hackpath, args_end);
	check_error_python(1);
	defer_decref(result);

	if (!result) return error("failure to invoke mmdata.parse()");

	if (PyObject_Not(result))
	{
		check_error_mmdata else return error("unknown error");
	}

	return 0;
}

error_code_t
mmagedit_write_rom(const char* path_to_rom)
{
	precheck_error_python(1);
	check_not_null(path_to_rom);

	PyObject* rompath = PyString(path_to_rom);
	defer_decref(rompath);

	PyObject* result = PyObject_CallMethodObjArgsString(g_data, "write", rompath, args_end);
	check_error_python(1);
	defer_decref(result);

	if (!result) return error("failure to invoke mmdata.write()");

	if (PyObject_Not(result))
	{
		check_error_mmdata else return error("unknown error");
	}

	return 0;
}

error_code_t
mmagedit_write_hack(const char* path_to_hack, bool oall)
{
	precheck_error_python(1);
	check_not_null(path_to_hack);

	PyObject* hackpath = PyString(path_to_hack);
	defer_decref(hackpath);

	PyObject* pyoall = PyBool_FromLong(oall);
	defer_decref(pyoall);

	PyObject* result = PyObject_CallMethodObjArgsString(g_data, "stat", hackpath, pyoall, args_end);
	check_error_python(1);
	defer_decref(result);

	if (!result) return error("failure to invoke mmdata.stat()");

	if (PyObject_Not(result))
	{
		check_error_mmdata else return error("unknown error");
	}

	return 0;
}

json_t
mmagedit_get_state()
{
	return mmagedit_get_state_select("");
}

json_t
mmagedit_get_state_select(const char* jsonpath)
{
	precheck_error_python("null");
	check_not_null_rv(jsonpath, "null");

	PyObject* pyjsonpath = PyString(jsonpath);
	defer_decref(pyjsonpath);

	PyObject* result = PyObject_CallMethodObjArgsString(g_data, "serialize_json_str", pyjsonpath, args_end);
	check_error_python("null");
	defer_decref(result);

	check_error_mmdata_rval("null");

	return store_string(PyObject_AsString(result));
}

error_code_t
mmagedit_apply_state(json_t json)
{
	precheck_error_python(1);
	
	PyObject* str = PyString(json);
	defer_decref(str);
	if (!str) return error("unable to create PyString");

	PyObject* result = PyObject_CallMethodObjArgsString(g_data, "deserialize_json_str", str, args_end);
	defer_decref(result);
	check_error_python(1)

	if (!result) return error("no result from deserialize_json_str");

	if (PyObject_Not(result))
	{
		check_error_mmdata else return error("unknown error");
	}

	return 0;
}

medtile_idx_t
mmagedit_get_mirror_tile_idx(world_idx_t idx, medtile_idx_t in)
{
	// validation
	if (in < 0) return error("negative medtile idx forbidden.", -1);

	precheck_error_python(-1);

	PyObjectBorrowed* world = get_world(idx);
	if (!world)
	{
		return error("No such world exists", -1);
	}

	PyObject* pyin = PyLong_FromLong(in);
	defer_decref(pyin);

	PyObject* retval = PyObject_CallMethodObjArgsString(world, "mirror_tile", pyin, args_end);
	defer_decref(retval);

	medtile_idx_t rv = PyLong_AsLong(retval);
	if (rv < 0) return error("Invalid mirror tile return", -1);

	return rv;
}

namespace
{
	int g_hello_world_int = 0;
	std::string g_hello_world_str = "Hello, World!";
}

void
mmagedit_hw_set_int(int c) 
{
	g_hello_world_int = c;
}

int
mmagedit_hw_get_int()
{
	return g_hello_world_int;
}

const char*
mmagedit_hw_get_str()
{
	return g_hello_world_str.c_str();
}

void
mmagedit_hw_set_str(const wchar_t* s)
{
	if (!s)
	{
		g_hello_world_str = "(null)";
	}
	else
	{
		g_hello_world_str = s;
	}
}

// just a simple test main function
// usage: mmagedit /path/to/mmagedit.py [base.nes] [hack.txt]
static int execmain(int argc, char** argv)
{
	if (argc == 1)
	{
		std::cout << "usage: mmagedit /path/to/mmagedit.py [base.nes] [hack.txt]" << std::endl;
		return 5;
	}
	mmagedit_set_log_level(5);
	if (mmagedit_init(argv[1])) return 1;
	std::cout << mmagedit_get_name_version_date() << std::endl;
	std::cout << mmagedit_get_version_int() << std::endl;
	if (argc > 2) {if (!mmagedit_load_rom(argv[2])) std::cout << "successfully loaded rom" << std::endl; else return 2;}
	if (argc > 3) {if (!mmagedit_load_hack(argv[3])) std::cout << "successfully loaded hack" << std::endl; else return 3;}
	if (argc > 2)
	{
		std::cout << mmagedit_get_state_select(".chr[0][0:2]") << std::endl;

		std::cout << mmagedit_get_state_select(".config.mapper-extension") << std::endl;
		mmagedit_apply_state("{\"config\": {\"mapper-extension\": true}}");
		std::cout << mmagedit_get_state_select(".config.mapper-extension") << std::endl;
	}
	mmagedit_end();
	return 0;
}

#ifdef MAIN
int main(int argc, char** argv)
{
	return execmain(argc, argv);
}
#endif