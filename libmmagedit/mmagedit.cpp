#include "mmagedit.h"

#include <stdio.h>
#include <iostream>
#include <Python.h>
#include "defer.h"

namespace
{
	int g_log_level = 0;
	const int LOG_TRIVIAL = 5;

	template<typename T>
	void log(T val, int level = LOG_TRIVIAL)
	{
		if (level <= g_log_level)
		{
			std::cout << val << std::endl;
		}
	}

	// used to hold string references that are
	// returned by library functions.
	std::string g_static_string_out;

	std::string g_error;
}

const char*
mmagedit_get_error()
{
	g_static_string_out = g_error;
	g_error = "";
	return g_static_string_out.c_str();
}

void mmagedit_set_log_level(int l)
{
	g_log_level = l;
}

int mmagedit_init(const char* path_to_mmagedit)
{
	log("initializing libpython...");
	Py_Initialize();
	log("done.");

	// set arg0 to path to mmagedit.py
	// set arg1 to "--as-lib"
	wchar_t* args[2] {
		Py_DecodeLocale(path_to_mmagedit, nullptr),
		Py_DecodeLocale("--as-lib", nullptr)
	};
	defer(PyMem_RawFree(args[0]));
	defer(PyMem_RawFree(args[1]));
	PySys_SetArgv(2, args);

	// run mmagedit.py
	FILE* f = fopen(path_to_mmagedit, "r");
	defer(fclose(f));

	log("loading mmagedit...");
	PyRun_AnyFile(f, path_to_mmagedit);
	log("done.");

	return 0;
}

int mmagedit_end()
{
	Py_Finalize();

	return 0;
}

const char*
mmagedit_get_name_version_date()
{
	// TODO
	return "";
}

unsigned long int
mmagedit_get_version_int()
{
	// TODO
	return 0;
}

error_code_t
mmagedit_load_rom(const char* path_to_rom)
{
	// TODO
	return 0;
}

error_code_t
mmagedit_load_hack(const char* path_to_hack)
{
	// TODO
	return 0;
}

json_t
mmagedit_get_state()
{
	// TODO
	return "{}";
}

error_code_t
mmagedit_apply_state(json_t)
{
	// TODO
	return 0;
}

namespace
{
	int g_hello_world_int;
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
	return "Hello, World!";
}

static int execmain(int argc, char** argv)
{
	mmagedit_set_log_level(5);
	mmagedit_init(argc > 1 ? argv[1] : "./mmagedit.py");
	std::cout << mmagedit_get_name_version_date() << std::endl;
	mmagedit_end();
	return 0;
}

#ifdef MAIN
int main(int argc, char** argv)
{
	return execmain(argc, argv);
}
#endif