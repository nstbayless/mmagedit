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

// nonzero indicates an error.
typedef int error_code_t;

// indicates string should contain valid json.
// if string contains only "null", check for an error with mmagedit_get_error
typedef const char* json_t;

// All returned strings are valid references until the next library call is made.

// This must be called before any other function
// parameters:
//   path_to_mmagedit: path to mmagedit.py
external error_code_t
mmagedit_init(const char* path_to_mmagedit);

// this should be called to shut down the library
external error_code_t
mmagedit_end();

// returns e.g. "MMagedit v1.21: 12 March 2021"
// this invokes a python function, which can be used to verify that the
// python context is working correctly.
external const char*
mmagedit_get_name_version_date();

// retrieves format int from mmagedit.
// This int is stored in the hack file, which can be used to check the version mmagedit
// that the hack was created in.
external unsigned long int
mmagedit_get_version_int();

// load a base rom.
external error_code_t
mmagedit_load_rom(const char* path_to_rom);

// load a hack file (optional)
external error_code_t
mmagedit_load_hack(const char* path_to_hack);

// write a rom.
external error_code_t
mmagedit_write_rom(const char* path_to_rom);

// write a hack file
// if "all" is false, certain details will be withheld from the hack file if they
// have not been changed from the base ROM, including CHR data.
external error_code_t
mmagedit_write_hack(const char* path_to_hack, bool all);

// returns a json string containing all the data in the current state of the hack
external json_t
mmagedit_get_state();

// all the json data in this string will be applied to the current state of the hack.
// any data which is left out of this json object will not modify the state of the hack.
external error_code_t
mmagedit_apply_state(json_t);

// if an error occured previously, use this to get its error description.
// if no errors have occurred, this returns an empty string.
external const char*
mmagedit_get_error();

// set log level (default is 0 -- print nothing)
// (this can be set before init)
#define LOG_NONE 0
#define LOG_ERROR 3
#define LOG_TRIVIAL 5

external void
mmagedit_set_log_level(int loglevel);

// "hello world" functions which can be used to verify library integrity

// store and retrieve an int
external void
mmagedit_hw_set_int(int);
external int
mmagedit_hw_get_int();

// this should return the string "Hello, World!"
external const char*
mmagedit_hw_get_str();