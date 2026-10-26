namespace daedalus { namespace sol {
enum class Error { None, Missing };
struct Result { Error Failure = Error::None; };
}}
