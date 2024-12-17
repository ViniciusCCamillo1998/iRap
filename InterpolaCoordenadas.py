import os
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import xml.etree.ElementTree as ET
from tkinter import filedialog, messagebox
from haversine import haversine, Unit
from tqdm import tqdm
import requests


# Função para interpolar coordenadas.
def interpolate_coords(df, erro_max):
    interpolated_data = []

    for i in range(len(df) - 1):
        start = df.iloc[i].values
        end = df.iloc[i + 1].values
        interpolated_data.extend(interpolate_between_points(start, end, erro_max))

    # Adicionar o último ponto
    interpolated_data.append(df.iloc[-1].values)

    # Criar um DataFrame com as coordenadas interpoladas
    interpolated_df = pd.DataFrame(interpolated_data, columns=['Latitude', 'Longitude', 'Altitude'])
    
    return interpolated_df


# Função auxiliar para interpolar entre dois pontos
def interpolate_between_points(start, end, erro_max):
    coords = [start]
    total_distance = geodesic(start[:2], end[:2]).meters
    
    if total_distance > erro_max:
        num_points = int(np.ceil(total_distance / erro_max))
        lat_points = np.linspace(start[0], end[0], num_points + 1)[1:]
        lon_points = np.linspace(start[1], end[1], num_points + 1)[1:]
        alt_points = np.linspace(start[2], end[2], num_points + 1)[1:]
        
        for lat, lon, alt in zip(lat_points, lon_points, alt_points):
            coords.append((lat, lon, alt))
    
    return coords


# Função principal para ler o KML e processar as coordenadas
def process_kml(kml_file, erro_max):
    # Parse do arquivo KML
    tree = ET.parse(kml_file)
    root = tree.getroot()

    # Namespace do KML
    namespace = {'kml': 'http://www.opengis.net/kml/2.2'}

    # Encontrar todas as coordenadas
    coordinates = root.find('.//kml:coordinates', namespace).text.strip()

    # Separar as coordenadas em uma lista
    coord_list = coordinates.split()

    # Separar latitude, longitude e altitude em colunas diferentes
    data = []
    for coord in coord_list:
        lon, lat, alt = map(float, coord.split(','))
        data.append([lat, lon, alt])

    # Criar um DataFrame com as coordenadas
    df = pd.DataFrame(data, columns=['Latitude', 'Longitude', 'Altitude'])

    # Interpolar as coordenadas
    interpolated_df = interpolate_coords(df, erro_max)

    return interpolated_df


# Função para filtrar coordenadas com espaçamento máximo.
def filter_coords(df, max_distance):
    filtered_data = [df.iloc[0].values]  # Começa com o primeiro ponto
    
    last_point = df.iloc[0].values
    for i in tqdm(range(1, len(df))):
        current_point = df.iloc[i].values
        distance = geodesic(last_point[:2], current_point[:2]).meters
        
        if distance >= max_distance:
            filtered_data.append(current_point)
            last_point = current_point

    # Adicionar o último ponto, se não estiver já incluído
    if (filtered_data[-1] != df.iloc[-1].values).any():
        filtered_data.append(df.iloc[-1].values)

    # Criar um DataFrame com as coordenadas filtradas
    filtered_df = pd.DataFrame(filtered_data, columns=['Latitude', 'Longitude', 'Altitude'])

    return filtered_df


def get_elevation(latitude, longitude):
    try:
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={latitude},{longitude}"
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()['results'][0]
            return result['elevation']
        else:
            return np.nan
        
    except:
        return np.nan
    

def interpol_altitude(df):
    # Inicializa a coluna de altitude
    df['Altitude'] = np.nan

    # Variável para acumular a distância
    distancia_acumulada = 0

    # Iterar sobre o DataFrame para calcular as altitudes
    for i in tqdm(range(len(df))):
        distancia_acumulada += df.loc[i, 'Distância (m)']
        
        # Quando a distância acumulada atingir ou exceder 200 metros, buscar a altitude
        if distancia_acumulada >= 200:
            latitude = df.loc[i, 'Latitude']
            longitude = df.loc[i, 'Longitude']
            altitude = get_elevation(latitude, longitude)
            df.loc[i, 'Altitude'] = altitude
            
            # Resetar o acumulador
            distancia_acumulada = 0

    # Garantindo que o inicio e fim tenham valores
    linhas = df.shape[0] - 1
    df['Altitude'][0] = get_elevation(df['Latitude'][0], df['Longitude'][0])
    df['Altitude'][linhas] = get_elevation(df['Latitude'][linhas], df['Longitude'][linhas])

    return df
# ------------------------------------------------------------------------------------------------------------
# ---------------------------------------------- Exemplo de uso ----------------------------------------------
# ------------------------------------------------------------------------------------------------------------

kml_file = filedialog.askopenfilename(title="Selecione o arquivo KML com o segmento a interpolar coordenadas")

if kml_file.endswith('.kml'):
    print("Arquivo selecionado: " + kml_file)
    max_distance = float(input("Digite o espaçamento desejado das coordenadas em metros: "))
    erro_max = max_distance/1000

    alt = str(input("Interpolar altitude (y/n): "))

    print('\nExtraindo coordenadas do KML')
    df_interpolated = filter_coords(process_kml(kml_file, erro_max), max_distance)

    # Calcular a distância entre cada linha e a anterior
    df_interpolated['Distância (m)'] = df_interpolated.apply(lambda row: haversine(
        (df_interpolated.iloc[row.name - 1]['Latitude'], df_interpolated.iloc[row.name - 1]['Longitude']),
        (row['Latitude'], row['Longitude']),
        unit=Unit.KILOMETERS
        ) if row.name > 0 else None, axis=1)
    
    # Calcula distancias em m
    df_interpolated['Distância (m)'] = df_interpolated['Distância (m)']*1000
    df_interpolated['Distância (m)'].fillna(0, inplace=True)

    # Busca altitude se essa for tudo 0 e o usuário solicitar
    if alt.lower() == 'y':
        if (df_interpolated['Altitude'] == 0).all():
            print('\nObtendo altitude online')
            df_interpolated = interpol_altitude(df_interpolated)
    
    # Interpolar os valores NaN na coluna de altitude
    df_interpolated['Altitude'] = df_interpolated['Altitude'].interpolate(method='linear')
    df_interpolated['Altitude'].fillna(0, inplace=True)

    # Exportando
    nome = os.path.join(os.path.dirname(kml_file), os.path.basename(kml_file)[:-4] + " - " + str(max_distance) + "m.xlsx")
    df_interpolated.to_excel(nome)
    messagebox.showinfo("Sucesso!", "Coordenadas interpoladas!")

else:
    messagebox.showerror("Erro!", "Arquivo inválido. Por favor, selecione um arquivo KML.")

