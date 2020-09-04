# -*- coding: utf-8 -*-


class ParseError(Exception):
    """
    Parse error Invalid JSON was received by the server.
    An error occurred on the server while parsing the JSON text.
    """
    pass


class InvalidRequestError(Exception):
    """
    Invalid Request The JSON sent is not a valid Request object.
    """
    pass


class MethodNotFound(Exception):
    """
    The method does not exist / is not available.
    """
    pass


class InvalidParamsError(Exception):
    """
    Invalid method parameter(s).
    """
    pass


class InternalError(Exception):
    """
    Internal JSON-RPC error.
    """
    pass


class ServerError(Exception):
    """
    Reserved for implementation-defined server-errors.
    """
    pass


class ClientError(Exception):
    """
    The 4xx class of status code is intended for cases in which the client
    seems to have erred. Except when responding to a HEAD request, the server
    should include an entity containing an explanation of the error situation,
    and whether it is a temporary or permanent condition. These status codes
    are applicable to any request method. User agents should display any
    included entity to the user.
    """
    pass


class ResponseError(Exception):
    """
    raise ResponseError When a call encounters an error
    """
    pass
