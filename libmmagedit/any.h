#include <functional>
#include <typeinfo>

class any {

	typedef int type_t;

public:
	#define register_any_type(T) template<> struct any::trait<T> {const static type_t type = __COUNTER__;}
	template<typename T> struct trait;

	type_t m_type = -1;
	char m_value[8];

	any(void) {}

	template<typename T>
	any(const T& t) { set(t); }

	// implicit cast
	template<typename T>
	operator T() const {
		T t;
		if (!get(t))
		{
			throw std::bad_cast();
		}
		return t;
	}

	template<typename T>
	void set(const T& t)
	{
		m_type = trait<T>::type;
		static_assert(sizeof(m_value) >= sizeof(T));
		*reinterpret_cast<T*>(&m_value) = t;
	}

	template<typename T>
	bool get(T& t) const
	{
		// type mismatch.
		if (!is<T>()) return false;
		t = *reinterpret_cast<const T*>(&m_value);
		return true;
	}

	template<typename T>
	bool is() const
	{
		return m_type == trait<T>::type;
	}
};


template<typename rtype>
class retv {
public:
  template<typename... Args>
  using func_t = std::function<rtype(Args...)>;

	template<typename T=int>
	static any anyfunc(func_t<> f, ...)
	{
		return f();
	}

	template<typename Arg>
	static any anyfunc(func_t<Arg> f, const any* v)
	{
		return f(v[0]);
	}

	template<typename Arg, typename... Args>
	static any anyfunc(func_t<Arg, Args...> f, const any* v)
	{
    // recurse using lambda, which takes one less argument.
		return anyfunc<Args...>(
			[f, v](Args... args) -> rtype {
        return f(*v, args...);
      },
      v + 1
    );
	}

  // this explicitly aids in
  // casting function pointers to std function.
  template<typename... Args>
	static any anyfunc(rtype(*f)(Args...), const any* v)
	{
    // convert to f std::function
    const std::function<rtype(Args...)> function{ f };
    return anyfunc<Args...>(function, v);
	}
};

// special case for void
template<>
class retv<void> {
public:
  using rtype = void;
	template<typename... Args>
  using func_t = std::function<rtype(Args...)>;

	template<typename T=int>
	static any anyfunc(func_t<> f, ...)
	{
		return f(), any{};
	}

	template<typename Arg>
	static any anyfunc(func_t<Arg> f, const any* v)
	{
		return f(v[0]), any{};
	}

	template<typename Arg, typename... Args>
	static any anyfunc(func_t<Arg, Args...> f, const any* v)
	{
    // recurse using lambda, which takes one less argument.
		return anyfunc<Args...>(
			[f, v](Args... args) -> rtype {
        f(*v, args...);
      },
      v + 1
    );
	}

  // this explicitly aids in
  // casting function pointers to std function.
  template<typename... Args>
	static any anyfunc(rtype(*f)(Args...), const any* v)
	{
    // convert to f std::function
    const std::function<rtype(Args...)> function{ f };
    return anyfunc<Args...>(function, v);
	}
};