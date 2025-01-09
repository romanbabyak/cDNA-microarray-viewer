# ismed2024Z_zad2_Babiak_Marciniak

## Instrukcja uruchomienia programu
Python: Wersja 3.8 lub nowsza

1. Stworzenie i aktywowanie wirtualnego środowiska:

```
python -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate     # Windows
```


2. Instalacja zależności:
`pip install -r requirements.txt`

3. Program uruchamia się za pomocą pliku **main.py**.

## Krótki opis programu:

Program umożliwia załadowanie oraz wyświetlenie plików typu **tif**. Jest dedykowany do prezentacji obrazów będących wynikiem odczytu mikromacierzy cDNA z dwóch znaczników: **Cy3** i **Cy5**. 

Funkcjonalności programu obejmują:
- Jednoczesne wczytanie obu obrazów
- Wyświetlenie każdego z nich w odpowiedniej palecie barwnej:
  - Odcienie zieleni dla kanału **Cy3**
  - Odcienie czerwieni dla kanału **Cy5**
- Wyświetlenie obrazu sumarycznego, będącego efektem nałożenia obu kanałów
- Możliwość przybliżania wybranych fragmentów obrazu
- Zmianę parametrów wyświetlania (szerokości i położenia środka okna kontrastu)