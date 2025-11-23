_args_pended = None
_kwargs_pended = None

def print_with_pended(*args, **kwargs) -> None:
    if _args_pended is not None:
        print(*_args_pended, **_kwargs_pended)
        print_unpend()
    print(*args, **kwargs)

def print_pend(*args, **kwargs) -> None:
    global _args_pended, _kwargs_pended
    _args_pended = args
    _kwargs_pended = kwargs

def print_unpend() -> None:
    global _args_pended, _kwargs_pended
    _args_pended = None
    _kwargs_pended = None
