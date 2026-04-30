import flet as ft


def main(page: ft.Page):
    page.title = "PlayBook"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    welcome_text = ft.Text(
        "Добро пожаловать в PlayBook!",
        size=24,
        weight=ft.FontWeight.BOLD,
    )
    page.add(welcome_text)

    def button_clicked(e):
        welcome_text.value = "Отличноб Flet работает!"
        page.update()

    page.add(ft.ElevatedButton("Нажми меня", on_click=button_clicked))


ft.app(target=main)
