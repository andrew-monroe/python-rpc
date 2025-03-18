from dataclasses import dataclass
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


USERS_DICT = {
    "bob": {
        "permissions": ["read"],
    },
    "alice": {
        "permissions": ["read", "write"],
    },
}


# This would be a generic implementation of an authorization strategy that
# is intended to be ignorant of the actual data structure of a request.
@dataclass
class GenericAuthContext:
    user: str

    @staticmethod
    def authorize(request: FakeRequest, has_permissions: list[str], bar: int):
        username = request.url.split("/")[-1]

        if username not in USERS_DICT:
            raise Exception("Unauthorized.")
        user = USERS_DICT[username]

        # Example of a permission check.
        if not all(perm in user["permissions"] for perm in has_permissions):
            raise Exception("Unauthorized.")

        # Example of a data check.
        if bar % 2 != 0:
            raise Exception("Unauthorized.")

        return GenericAuthContext(user=username)


# Struct defining the expected shape of the input data.
class ExampleInput(Struct):
    foo: str
    bar: int

    # The authorize method maps the actual input data on the request into the
    # expected params for the authorization strategy.
    def authorize(self, request: FakeRequest) -> GenericAuthContext:
        return GenericAuthContext.authorize(
            request, has_permissions=["read", "write"], bar=self.bar
        )


# Struct defining the expected shape of the output data.
class ExampleOutput(Struct):
    fizz: float
    buzz: str


# The decorator definition that:
# 1. Validates the input data from the HTTP request.
# 2. Authorize and create the auth context.
# 3. Calls the decorated function with the intialized auth context instance
#   and the validated input data.
# 4. Encodes the result back to a string, and returns it.
def rpc(func):
    def inner(request: FakeRequest):
        validated_input = json.decode(request.body, type=func.__annotations__["schema"])

        # Authorize and create the auth context.
        ctx = validated_input.authorize(request)

        # Ensure the context is of the type expected by the function.
        assert isinstance(ctx, func.__annotations__["ctx"])

        # RPC(
        #     description=func.__doc__,
        #     input_schema=json.schema(func.__annotations__["schema"]),
        #     name=func.__name__,
        #     output_schema=json.schema(func.__annotations__["return"]),
        # )

        return json.encode(func(ctx=ctx, schema=validated_input))

    return inner


@rpc
def myFunc(schema: ExampleInput, ctx: GenericAuthContext) -> ExampleOutput:
    """
    This is a function!
    """
    print(ctx.user, schema.foo, schema.bar)

    return ExampleOutput(fizz=schema.bar / 2.0, buzz=schema.foo.capitalize())


print(
    myFunc(
        FakeRequest(
            url="https://example.com/alice", body='{ "foo": "hElLo", "bar": 1234 }'
        )
    )
)
