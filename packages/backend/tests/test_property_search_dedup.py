from myhome.property_search_dedup import fingerprint, url_key


def test_url_key_strips_tracking():
    assert url_key("https://WWW.Nepremicnine.net/oglasi/x/?utm_source=a&id=5#top") == "https://nepremicnine.net/oglasi/x?id=5"


def test_url_key_sorts_params_and_drops_click_ids():
    assert url_key("http://a.si/p?b=2&fbclid=z&a=1") == url_key("http://a.si/p?a=1&b=2")


def test_url_key_root_path():
    assert url_key("https://a.si/") == "https://a.si"


def test_fingerprint_none_when_sparse():
    assert fingerprint("land", None, 800, None, "Novo Mesto") is None
    assert fingerprint("land", 150000, None, None, "Novo Mesto") is None


def test_fingerprint_matches_across_sites():
    assert fingerprint("land", 149_500, 812, None, "Novo mesto, Slovenija") == fingerprint("land", 150_000, 808, None, "NOVO MESTO")


def test_fingerprint_strips_accents():
    assert fingerprint("house", 300000, None, 120, "Šentjernej") == fingerprint("house", 300000, None, 120, "sentjernej")


def test_fingerprint_differs_by_town():
    assert fingerprint("land", 150000, 800, None, "Novo Mesto") != fingerprint("land", 150000, 800, None, "Ljubljana")
