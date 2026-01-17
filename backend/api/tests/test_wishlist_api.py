def test_add_product_to_wishlist(auth_client, product):
    res = auth_client.post("/api/wishlist/", {
        "product_id": product.id
    })
    assert res.status_code == 201


def test_cannot_add_duplicate_wishlist(auth_client, product):
    auth_client.post("/api/wishlist/", {"product_id": product.id})
    res = auth_client.post("/api/wishlist/", {"product_id": product.id})
    assert res.status_code == 400


def test_list_wishlist(auth_client, product):
    auth_client.post("/api/wishlist/", {"product_id": product.id})
    res = auth_client.get("/api/wishlist/")
    assert res.status_code == 200
    assert len(res.data) == 1


def test_remove_wishlist_item(auth_client, product):
    auth_client.post("/api/wishlist/", {"product_id": product.id})
    res = auth_client.delete(f"/api/wishlist/{product.id}/")
    assert res.status_code == 204


def test_user_cannot_see_other_users_wishlist(
    auth_client, another_user_client, product
):
    auth_client.post("/api/wishlist/", {"product_id": product.id})
    res = another_user_client.get("/api/wishlist/")
    assert len(res.data) == 0
