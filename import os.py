import os
import subprocess

def upload_files_to_github(repo_path, repo_url, branch_name="main"):
    os.chdir(repo_path)
    
    try:
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=True)
            print("✔ Репозиторий Git успешно инициализирован.")
        else:
            print("ℹ Репозиторий Git уже существует в этой папке.")

        subprocess.run(["git", "branch", "-M", branch_name], check=True)

        remotes = subprocess.run(["git", "remote"], capture_output=True, text=True).stdout
        if "origin" not in remotes:
            subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
            print(f"✔ Удаленный репозиторий привязан: {repo_url}")
        else:
            print("ℹ Удаленный репозиторий 'origin' уже настроен.")

        subprocess.run(["git", "add", "."], check=True)
        print("✔ Все файлы добавлены (git add).")

        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if status.strip():
            subprocess.run(["git", "commit", "-m", "Первая загрузка файлов через Python"], check=True)
            print("✔ Коммит успешно создан.")
        else:
            print("ℹ Изменений для коммита не найдено, файлы уже закоммичены.")

        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
        print("Файлы успешно отправлены на GitHub!")

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды Git: {e}")

if __name__ == "__main__":
    PROJECT_PATH = r"C:\Users\Lenovo\Desktop\movie-bot" 
    
    REPO_URL = "https://github.com/bekarysssss/telegram-movie-bot"
    
    upload_files_to_github(PROJECT_PATH, REPO_URL)