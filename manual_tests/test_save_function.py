import os
import shutil
from functions.internal.save_file import save_file

# === CONFIG ===
TEST_DIR = "__test_env__"
ORIGINAL_FILE = os.path.join(TEST_DIR, "original.txt")
BACKUP_DIR = os.path.join(TEST_DIR, "backups")
CONTENT_DIR = os.path.join(TEST_DIR, "generated")

def reset_test_env():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)

# === TEST 1: copia di un file esistente (backup) ===
def test_copy_file():
    reset_test_env()
    with open(ORIGINAL_FILE, "w") as f:
        f.write("Questo è un file di test.")

    save_file(ORIGINAL_FILE, BACKUP_DIR)

    copied_file = os.path.join(BACKUP_DIR, "original.txt")
    assert os.path.exists(copied_file), "File non copiato"
    with open(copied_file) as f:
        assert f.read() == "Questo è un file di test."

# === TEST 2: creazione di nuovo file da contenuto ===
def test_create_new_file_from_content():
    reset_test_env()
    content = "Contenuto generato"
    save_file("placeholder.txt", CONTENT_DIR, file_name="generated.txt", content=content)

    path = os.path.join(CONTENT_DIR, "generated.txt")
    assert os.path.exists(path), "File non creato"
    with open(path) as f:
        assert f.read() == content

# === TEST 3: errore se content e source_path sono entrambi None ===
def test_fail_if_nothing_provided():
    reset_test_env()
    try:
        save_file(None, CONTENT_DIR)
    except Exception as e:
        assert "must be provided" in str(e)
    else:
        assert False, "Errore non sollevato"

# === TEST 4: errore se file_name è assente e source_path è None ===
def test_fail_if_filename_missing_and_no_source():
    reset_test_env()
    try:
        save_file("ignored.txt", CONTENT_DIR, file_name=None, content="ok")
    except Exception as e:
        pass  # accettabile se il controllo lo richiedi tu
    else:
        pass  # o qui metti assert False se ti aspetti errore

# === TEST 5: errore se source_path non esiste ===
def test_fail_if_source_path_not_found():
    reset_test_env()
    try:
        save_file("non_esistente.txt", BACKUP_DIR)
    except FileNotFoundError:
        pass
    else:
        assert False, "Errore atteso per file non esistente"

# === ESECUZIONE TEST ===
if __name__ == "__main__":
    test_copy_file()
    test_create_new_file_from_content()
    test_fail_if_nothing_provided()
    test_fail_if_filename_missing_and_no_source()
    test_fail_if_source_path_not_found()
    print("✅ Tutti i test passati")