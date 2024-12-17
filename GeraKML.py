# ----------------------- BIBLIOTECAS -----------------------
import pandas as pd
import numpy as np
import os
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
import xml.etree.ElementTree as ET
from tkinter import filedialog, messagebox
#pyinstaller main.py --hidden-import='sklearn.utils._vector_sentinel'


# ----------------------- FUNÇÕES -----------------------
class CreateKML:
    def __init__(self, file_path, kml_path):
        self.file_path = file_path
        self.kml_path = kml_path
        self.info_adicionais = {}
        self.sentido = {}
        
    def SimilarityMeter(self, text1, text2):
        # Avoiding erros with symbols
        for symbol in ((">", "maior"), ("<", "menor"), ("+", "mais"), ("-", "traco"), ("ç", "c"), ("ã", "a")):
            text1 = text1.replace(symbol[0], symbol[1])
            text2 = text2.replace(symbol[0], symbol[1])

        # Comparing words similarity
        to_vect = CountVectorizer(analyzer='word', ngram_range=(1,2))
        x1, x2 = to_vect.fit_transform([text1, text2])
        t1, t2 = x1.toarray(), x2.toarray()
        min = np.amin([t1, t2], axis=0)
        sum = np.sum(min)
        count = np.sum([t1, t2][0])
        to_mean = sum/count

        return to_mean

    def FileFilter(self, path):
        # Filtering files between accepted formats - xlsx, xls and csv
        files_path = []
        for filename in os.listdir(path):
            if filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv'):
                files_path.append(os.path.join(path, filename))
        return files_path

    def interpolate_with_previous_two_rows(self, df):
        df.reset_index(drop=True, inplace=True)
        df["ProxLat"] = df["Latitude"].shift(-1)
        df["ProxLon"] = df["Longitude"].shift(-1)

        for i in range(2, len(df)):
            for col in ["ProxLat", "ProxLon"]:
                if pd.isnull(df.at[i, col]):
                    df.at[i, col] = (df.at[i - 1, col] - df.at[i - 2, col]) + df.at[i - 1, col]
        return df

    def PreTreatment(self, df, countermeasures_types):
        # Only when Ultrapassar == 1
        df = df[df["Ultrapassar"] == 1]
        df.reset_index(drop=True, inplace=True)

        # Coordinates to numeric
        df["Latitude"] = df["Latitude"].str.replace(',', '.')
        df["Longitude"] = df["Longitude"].str.replace(',', '.')
        df["Distância"] = df["Distância"].str.replace(',', '.')

        df["Latitude"] = pd.to_numeric(df["Latitude"])
        df["Longitude"] = pd.to_numeric(df["Longitude"])
        df["Distância"] = pd.to_numeric(df["Distância"])

        df["ProxLat"] = 0
        df["ProxLon"] = 0

        # Comparing words similarity with all possibilities
        solutions = set(df['Contramedida'].tolist())
        tests = set(countermeasures_types['Nomenclatura'].tolist())
        temp_dict = {}
        for solution in solutions:
            temp_list = []
            for test in tests:
                temp_list.append(self.SimilarityMeter(solution, test))
            temp_dict[solution] = temp_list
        temp_df = pd.DataFrame.from_dict(temp_dict)
        temp_df.index = tests
        #temp_df.to_excel('SimilarityMeter.xlsx')

        # Adding solution format
        df['Formato de solucao'] = df['Contramedida']
        for colunm in solutions:
            equivalent = (colunm, temp_df[colunm].loc[temp_df[colunm] == temp_df[colunm].max()].index[0])
            solution_type = countermeasures_types['Formato'][countermeasures_types['Nomenclatura'] == equivalent[1]]
            df['Formato de solucao'].where(df['Formato de solucao'] != equivalent[0], solution_type.tolist()[0], inplace=True)
        
        # Cleaning dataframe
        df = df.drop(['FSI salvos a cada 100m por ano', 'FSI salvos a cada 100m no período de análise', 'Economia anual de custo de colisões', 
                      'Taxa de desconto', 'Valor Presente do Benefício da Segurança', 'Estimativa de custo', 'Custo estimado por período de análise', 
                      'Benefício líquido', 'BCR', 'TIR', 'Custo por FSI salvo', 'Imagem de Referência'], axis=1)
        
        return df

    def NextCoord(self, df_sh, df_sh_kml):
        df_sh_kml = self.interpolate_with_previous_two_rows(df_sh_kml)
        kms = set(df_sh["Distância"].tolist())
        for km in kms:
            lat = df_sh_kml.loc[df_sh_kml["Km"] == km, "ProxLat"].tolist()[0]
            lon = df_sh_kml.loc[df_sh_kml["Km"] == km, "ProxLon"].tolist()[0]
            df_sh["ProxLat"].where(df_sh["Distância"] != km, other=lat, inplace=True)
            df_sh["ProxLon"].where(df_sh["Distância"] != km, other=lon, inplace=True)
        
        return df_sh
    
    def AdjustDict(self, df, df_kml):
        # Separating files in three types of category
        dict_final = {}
        self.info_adicionais = {}
        self.sentido = {}
        roads = set(df["Via "].tolist())
        for road in roads:
            df_road = df[df['Via '] == road]
            df_road_kml = df_kml[df_kml['Road'] == road]
            shs = sorted(list(set(df_road["Trecho"].tolist())))
            dict_final[road] = {}
            self.info_adicionais[road] = {}
            self.sentido[road] = {}
            for sh in shs:
                df_sh = df_road[df_road['Trecho'] == sh]
                df_sh_kml = df_road_kml[df_road_kml['Section'] == sh]

                # Organizando proxima coordenada e sentido da via
                df_sh = self.NextCoord(df_sh, df_sh_kml)
                kms = df_sh["Distância"].tolist()
                self.sentido[road][sh] = kms[0] - kms[-1]
                # Sentido da via
                if kms[0] - kms[1] <= 0:
                    # Crescente
                    kms = sorted(list(set(kms)))
                else:
                    # Decrescente
                    kms = sorted(list(set(kms)), reverse=True)

                dict_final[road][sh] = {}
                self.info_adicionais[road][sh] = {}
                for km in kms:
                    df_km = df_sh[df_sh['Distância'] == km]
                    groups = sorted(list(set(df_km["Grupo Resumo de Contramedidas"].tolist())))
                    
                    if "Linear" in df_km["Formato de solucao"].tolist():
                        self.info_adicionais[road][sh][km] = ["Linear"]
                    else:
                        self.info_adicionais[road][sh][km] = ["Pontual"]

                    dict_final[road][sh][km] = {}
                    for group in groups:
                        df_group = df_km[df_km['Grupo Resumo de Contramedidas'] == group]
                        dict_final[road][sh][km][group] = df_group

        return dict_final

    def ReadDf(self):
        # Reading standard file with solutions types
        for file in os.listdir(os.getcwd()):
            if file.endswith("Custos - Contra Medidas.xlsx"):
                countermeasures_types = pd.read_excel(os.path.join(os.getcwd(), "Custos - Contra Medidas.xlsx"))
        
        # Extracting data from kml
        df_kml = self.extrair_dados_kml(self.kml_path)

        # Reading csv and excel files, followed by correction
        if self.file_path.endswith('.csv'):
            df = self.PreTreatment(pd.read_csv(self.file_path, delimiter=";", encoding='utf-8-sig'), countermeasures_types)
        else:
            df = self.PreTreatment(pd.read_excel(self.file_path), countermeasures_types)

        # Separating files into dictionaries
        dict_final = self.AdjustDict(df, df_kml)

        return dict_final

    def dataframe_para_kml(self, dict_final, path):

        for via in dict_final.keys():
            # Cria o elemento raiz do XML
            root = ET.Element("kml")

            # Adiciona o namespace xmlns
            root.set("xmlns", "http://www.opengis.net/kml/2.2")

            # Criado Document
            doc = ET.SubElement(root, "Document")
            doc_name = ET.SubElement(doc, "name")
            doc_name.text = via

            # Adiciona style padrão do arquivo
            style = ET.SubElement(doc, "Style")
            # Nome do style
            style.set("id", "normalPlacemark")
            # Formato do icone
            iconstyle = ET.SubElement(style, "IconStyle")
            icon = ET.SubElement(iconstyle, "Icon")
            href = ET.SubElement(icon, "href")
            href.text = "http://maps.google.com/mapfiles/kml/paddle/wht-blank.png"
            # Formatação da tabel
            table = ET.SubElement(style, "LabelStyle")
            table_color = ET.SubElement(table, "color")
            table_color.text = "ffffffff"
            table_scale = ET.SubElement(table, "scale")
            table_scale.text = "0.6"
            # Formatação Ballonn
            ballonn = ET.SubElement(style, "BalloonStyle")
            ballonn_text = ET.SubElement(ballonn, "text")
            ballonn_text.text = "$[description]"
            # Formatação das linhas
            style_line = ET.SubElement(doc, "Style")
            style_line.set("id", "BlueLine")
            line = ET.SubElement(style_line, "LineStyle")
            color = ET.SubElement(line, "color")
            color.text = "ffdc5705"
            width = ET.SubElement(line, "width")
            width.text = "4"

            # Cria o elemento "Folder" da trecho
            for trecho in dict_final[via].keys():
                folder_trecho = ET.SubElement(doc, "Folder")
                folder_trecho_name = ET.SubElement(folder_trecho, "name")
                folder_trecho_name.text = str(trecho)

                km_list = list(dict_final[via][trecho].keys())
                # Cria o marcado no km
                for km in range(len(km_list)):
                    # Cria os elementos
                    placemark = ET.SubElement(folder_trecho, "Placemark")
                    placemark_name = ET.SubElement(placemark, "name")
                    placemark_name.text = str(km_list[km])

                    placemark_style = ET.SubElement(placemark, "styleUrl")
                    placemark_style.text = "#normalPlacemark"

                    placemark_description = ET.SubElement(placemark, "description")
                    placemark_table = ET.SubElement(placemark_description, "table")
                    placemark_table.set("width", "400")
                    tr = ET.SubElement(placemark_table, "tr")
                    td_title = ET.SubElement(tr, "td")
                    td_title.set("style", "vertical-align: top;")
                    td_title_s = ET.SubElement(td_title, "strong")

                    if self.sentido[via][trecho] < 0:
                        next_km = str(round(km_list[km] + 0.1, 3))
                    else:
                        next_km = str(round(km_list[km] - 0.1, 3))

                    secao = "KM " + str(km_list[km]) + " AO KM " + next_km
                    td_title_s.text = "CONTRAMEDIDAS ADOTADAS NA SEÇÃO " + secao + ":"

                    # Criando tabela com as contramedidas no ponto
                    for grupo in dict_final[via][trecho][km_list[km]].keys():
                        tr = ET.SubElement(placemark_table, "tr")
                        td_title = ET.SubElement(tr, "td")
                        td_title.set("style", "vertical-align: top;")
                        td_title_s = ET.SubElement(td_title, "strong")
                        td_title_s.text = str(grupo)

                        for row in dict_final[via][trecho][km_list[km]][grupo]["Contramedida"].tolist():
                            tr = ET.SubElement(placemark_table, "tr")
                            td_key = ET.SubElement(tr, "td")
                            td_key.set("style", "vertical-align: top;")
                            td_key.text = "{}".format(row)

                    lat = dict_final[via][trecho][km_list[km]][grupo]["Latitude"].tolist()[0]
                    long = dict_final[via][trecho][km_list[km]][grupo]["Longitude"].tolist()[0]

                    point = ET.SubElement(placemark, "Point")
                    coords = ET.SubElement(point,"coordinates")
                    coords.text = "{0},{1},0".format(long, lat)

                    if "Linear" in self.info_adicionais[via][trecho][km_list[km]][0]:
                        prox_lat = dict_final[via][trecho][km_list[km]][grupo]["ProxLat"].tolist()[0]
                        prox_long = dict_final[via][trecho][km_list[km]][grupo]["ProxLon"].tolist()[0]

                        placemark_line = ET.SubElement(folder_trecho, "Placemark")
                        placemark_line_name = ET.SubElement(placemark_line, "name").text = secao
                        placemark_line_style = ET.SubElement(placemark_line, "styleUrl").text = "BlueLine"
                        placemark_line_string = ET.SubElement(placemark_line, "LineString")
                        placemark_line_coordinates = ET.SubElement(placemark_line_string, "coordinates").text = "{0},{1},0 {2},{3},0".format(long, lat, prox_long, prox_lat)

            tree = ET.ElementTree(root)

            # Salva o arquivo em formato KML
            tree.write(os.path.join(os.path.dirname(path), via + " - Contramedidas.kml"), encoding="utf-8", xml_declaration=True)
            print(os.path.join(os.path.dirname(path), via + " - Contramedidas.kml"))

            # Salva o XML no arquivo
            #tree.write(path, encoding="utf-8", xml_declaration=True)

    def extrair_dados_kml(self, caminho_arquivo):
        # Analisa o arquivo KML
        tree = ET.parse(caminho_arquivo)
        root = tree.getroot()

        # Define o namespace
        namespace = {'kml': 'http://www.opengis.net/kml/2.2'}

        # Encontra todos os elementos de Placemark no arquivo KML
        elementos_placemark = root.findall('.//kml:Placemark', namespaces=namespace)

        # Lista para armazenar os dados extraídos
        dados_extraidos = []

        # Itera sobre os elementos de Placemark e extrai dados
        for placemark in elementos_placemark:
            nome = placemark.find('.//kml:name', namespaces=namespace).text.strip()
            coordenadas_texto = placemark.find('.//kml:coordinates', namespaces=namespace).text.strip()
            coordenadas = [tuple(map(float, ponto.split(','))) for ponto in coordenadas_texto.split()]
            
            # Extrai os dados da tabela 'Road', 'Section' e 'Distance'
            tabela = placemark.find('.//kml:description', namespaces=namespace).text.strip() if placemark.find('.//kml:description', namespaces=namespace) is not None else None
            if tabela is not None:
                road = None
                section = None

                # Analisa o texto da tabela para extrair informações
                linhas = tabela.split('<tr>')
                for i in range(len(linhas)-1):
                    #print(linhas[i])
                    if 'Road:' in linhas[i]:
                        road = linhas[i].split('<td style="vertical-align: top;">')[2].split('</td>')[0].strip()
                        road = (road.split(">")[1]).split("<")[0]
                    elif 'Section:' in linhas[i]:
                        section = linhas[i].split('<td style="vertical-align: top;">')[2].split('</td>')[0].strip()

                # Adiciona os dados à lista
                for coord in coordenadas:
                    dados_extraidos.append((nome, coord[0], coord[1], road, section))
            else:
                # Adiciona os dados sem informações da tabela
                for coord in coordenadas:
                    dados_extraidos.append((nome, coord[0], coord[1], None, None))

        # Cria um DataFrame pandas
        df = pd.DataFrame(dados_extraidos, columns=['Km', 'Longitude', 'Latitude', 'Road', 'Section'])
        df["Longitude"] = pd.to_numeric(df["Longitude"])
        df["Latitude"] = pd.to_numeric(df["Latitude"])
        df["Km"] = pd.to_numeric(df["Km"])

        return df

def main():
    
    #file_path = r'C:\Users\Pavesys - MAQ70\Desktop\python\_IRAP\Geração de KMZ\ViDa\Lote 3 - Contramedidas.csv'
    #kml_path = r'C:\Users\Pavesys - MAQ70\Desktop\python\_IRAP\Geração de KMZ\ViDa\BID-SC-Lote3-Encadeamento.kml'

    file_path = filedialog.askopenfilename(title="Selecione o arquivo bruto (excel ou csv) com as contramedidas")
    kml_path = filedialog.askopenfilename(title="Selecione o encadeamento (.kml) referente ao arquivo de contramedidas")

    try:
        kmz_creator = CreateKML(file_path, kml_path)
        dict_final = kmz_creator.ReadDf()
        kmz_creator.dataframe_para_kml(dict_final, file_path)
        messagebox.showinfo(title="Processo finalizado", 
                            message="Arquivos KML gerados com sucesso")
    except:
        messagebox.showerror(title="Erro ao gerar arquivo KML",  
                            message="Ocorreu um erro durante a geração do arquivo KML")

def Teste():
    # FUNÇÃO PARA TESTE
    pass

if __name__ == "__main__":
    main()
    #Teste()

#https://www.earthpoint.us/exceltokml.aspx
#https://simplekml.readthedocs.io/en/latest/gettingstarted.html
