Example of usage in an endpoint::

    # get the name of the cache
    cache_name = endpoint._endpoint_cache_make_name("json")
    # check if the cache exists
    cached = endpoint._endpoint_cache_get(cache_name)
    if cached:
        result = cached
    else:
        result = json.dumps(env["my.model"]._get_a_very_expensive_computed_result())
        # cache does not exist, create it
        endpoint._endpoint_cache_store(cache_name, result)
    
    resp = Response(result, content_type="application/json", status=200)
    result = dict(response=resp)
