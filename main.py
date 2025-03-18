from msgspec import Struct, json

# Stand-in for actual django HttpRequest.
class FakeRequest(Struct):
    url: str
    body: str

# The data needed to define an RPC.
class RPC(Struct):
    input_schema: dict
    output_schema: dict
    name: str
    description: str

# This would be a generic implementation of an authorization strategy that
# is intended to be ignorant of the actual data structure of a request.
class GenericAuthorizer:
    user: str

    def __init__(self, request: FakeRequest, bar: int):
        if request.url == "https://example.com/user" and bar % 2 == 0:
            self.user = "USER!"
        else:
            raise Exception("Unauthorized.")

# Struct defining the expected shape of the input data.
class ExampleInput(Struct):
    foo: str
    bar: int

# Struct defining the expected shape of the output data.
class ExampleOutput(Struct):
    fizz: float
    buzz: str

# A _specific_ implementation of the GenericAuthorizer that deconstructs
# the validated input data to be passed in for authorization.
class MyAuthorizer(GenericAuthorizer):
    def __init__(self, request: FakeRequest, input: ExampleInput):
        super().__init__(request=request, bar=input.bar)

# The decorator definition that:
# 1. Validates the input data from the HTTP request.
# 2. Initializes the auth class, thereby performing authentication.
# 3. Calls the decorated function with the intialized authorizer instance
#   and the validated input data.
# 4. Encodes the result back to a string, and returns it.
def rpc(func):                                                                                            
    def inner(request: FakeRequest):
        validated_input = json.decode(request.body, type=func.__annotations__["input"])
        auth = func.__annotations__["auth"](request, validated_input)

        # RPC(
        #     description=func.__doc__,
        #     input_schema=json.schema(func.__annotations__["input"]),
        #     name=func.__name__,
        #     output_schema=json.schema(func.__annotations__["return"]),
        # )

        return json.encode(func(auth, validated_input))
    return inner

@rpc
def myFunc(auth: MyAuthorizer, input: ExampleInput) -> ExampleOutput:
    """
    This is a function!
    """
    print(auth.user, input.foo, input.bar)

    return ExampleOutput(
        fizz=input.bar / 2.0,
        buzz=input.foo.capitalize()
    )

print(myFunc(FakeRequest(
    url="https://example.com/user",
    body='{ "foo": "hElLo", "bar": 1234 }'
)))