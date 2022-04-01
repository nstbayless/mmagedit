#ifndef __cplusplus
    #define externC
#else
    #define externC extern "C"
#endif

#ifdef _WIN32
   #define external          \
      externC                \
      __declspec(dllexport)
#endif

#ifdef __linux__ 
   #define external          \
      externC             
#endif

#ifndef external
    #define external        \
        externC
#endif

#include <cstdint>

// nonzero indicates an error has occurred.
typedef int error_code_t;

// indicates string should contain valid json.
// if string contains only "null", check for an error with mmagedit_get_error_occurred()
typedef const char* json_t;

typedef int microtile_idx_t;
typedef int medtile_idx_t;
typedef int macrotile_idx_t;
typedef int level_idx_t;
typedef int world_idx_t;

// All returned strings are valid references until the next library call is made.

// This must be called before any other function
// parameters:
//   path_to_mmagedit: path to mmagedit.py
external error_code_t
mmagedit_init(const char* path_to_mmagedit);

// this should be called to shut down the library
external error_code_t
mmagedit_end();

// if an error occurred previously, this function will return 1.
// Otherwise, this function returns 0.
// mmagedit_get_error() can be used to determine the description of the error.
// mmagedit_clear_error() can be used to clear this error.
external int
mmagedit_get_error_occurred();

// if an error has occurred, this function clears it.
external void
mmagedit_clear_error();

// if an error occured previously, use this to get its error description.
// if no errors have occurred, this returns an empty string.
// the error is cleared after calling this function.
external const char*
mmagedit_get_error();

// returns e.g. "MMagedit v1.21: 12 March 2021"
// this invokes a python function, which can be used to verify that the
// python context is working correctly.
// returns an empty string if an error has occurred.
external const char*
mmagedit_get_name_version_date();

// retrieves format int from mmagedit.
// This int is stored in the hack file, which can be used to check the version mmagedit
// that the hack was created in.
// returns 0 if an error occurred.
external uint64_t
mmagedit_get_version_int();

// This retrieves the minimum format version that libmmagedit
// requires mmagedit to have.
// this can be run before mmagedit_init.
// (guaranteed no error.)
external uint64_t
mmagedit_get_minimum_version_int();

// load a base rom.
external error_code_t
mmagedit_load_rom(const char* path_to_rom);

// load a hack file (optional)
external error_code_t
mmagedit_load_hack(const char* path_to_hack);

// write a rom.
external error_code_t
mmagedit_write_rom(const char* path_to_rom);

// write an ips patch.
external error_code_t
mmagedit_write_patch(const char* path_to_patch);

// write a hack file
// if "all" is false, certain details will be withheld from the hack file if they
// have not been changed from the base ROM, including CHR data.
external error_code_t
mmagedit_write_hack(const char* path_to_hack, bool all);

// returns a json string containing all the data in the current state of the hack
// if an error occurs, the return value is the string containing "null"
// however, "null" is also a valid return value on its own  -- please use mmagedit_get_error_occured() to determine if a true error occurred.
external json_t
mmagedit_get_state();

// as above, but selected using a jsonpath.
// jsonpath may be of the format ".foo.bar[0].quz", etc.
//
// example jsonpaths:
//   ""                                 : returns full state
//   ".chr[0][4:23]"                    : returns only the CHR image data in page 0 (backgrounds) with indices in the range [4, 23)
//   ".worlds[0].max-symmetry-idx"      : returns max symmetry idx for world 0
//   ".levels[5].\".name\""             : returns ".name" field for level 5
external json_t
mmagedit_get_state_select(const char* jsonpath);

// all the json data in this string will be applied to the current state of the hack.
// any data which is left out of this json object will not modify the state of the hack.
external error_code_t
mmagedit_apply_state(json_t);

// get mirrored med-tile idx for given med-tile in the given world.
// returns -1 if an error occurred.
external medtile_idx_t
mmagedit_get_mirror_tile_idx(world_idx_t, medtile_idx_t);

// set log level (default is 0 -- log nothing)
// (this can be set before init)
#define LOG_NONE 0
#define LOG_ERROR 3
#define LOG_INFO 4
#define LOG_TRIVIAL 5

external void
mmagedit_set_log_level(int loglevel);

// pass 0 to disable logging to stdout
external void
mmagedit_set_log_stdout(int);

// sets the number of log lines to keep.
// default is 100.
// 0 means do not delete logs.
external void
mmagedit_set_log_count_max(int c);

// get current number of logs in buffer
external int
mmagedit_get_log_count(int c);

// retrieves the nth most recent log line.
// guaranteed no error.
// if n is out of bounds, an empty string is returned.
external const char*
mmagedit_get_log_entry(int n);

// retrieves the nth most recent log line's log-level.
// returns -1 if n is out of bounds.
external int
mmagedit_get_log_entry_level(int n);

// run the string of python code directly.
// returns nonzero on failure.
// no output is returned, but you can inspect local or global variables with
// the next functions in this header file.
// start is a python start token; refer to python C api documentation,
// or pass in 0 for a default.
// the variable mmdata contains the MMData object for this library.
external int
mmagedit_run_pystring(const char* str, int start);

// access local and global variables as int or string.
// pass 1 to read local and 0 to read global.
// use mmagedit_get_error_occurred() to check for errors.
external int
mmagedit_get_python_int(int local, const char* variable_name);

external const char*
mmagedit_get_python_str(int local, const char* variable_name);

// "hello world" functions which can be used to verify library integrity

// store and retrieve an int
external void
mmagedit_hw_set_int(int);
external int
mmagedit_hw_get_int();

// this should return the string "Hello, World!" or whatever was set previously
external const char*
mmagedit_hw_get_str();
external void
mmagedit_hw_set_str(const char*);