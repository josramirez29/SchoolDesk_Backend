from app.contrasenas import generar_hash, verificar_contrasena


def test_el_hash_no_contiene_la_contrasena_y_se_puede_verificar() -> None:
    hash_guardado = generar_hash("mi-contrasena")

    assert "mi-contrasena" not in hash_guardado
    assert verificar_contrasena("mi-contrasena", hash_guardado)
    assert not verificar_contrasena("otra-contrasena", hash_guardado)


def test_la_misma_contrasena_genera_hashes_distintos() -> None:
    # Por la sal aleatoria: dos usuarios con la misma contraseña no se delatan.
    assert generar_hash("igual") != generar_hash("igual")
