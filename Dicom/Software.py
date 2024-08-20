import os
import shutil
from collections import defaultdict
import pydicom
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


class DICOMViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DICOM Viewer con Recorte Manual")
        self.root.geometry("900x700")

        # Variables
        self.dicom_folder = ""
        self.dicom_files_by_series = defaultdict(list)
        self.image_refs = []  # Lista para mantener las referencias de las imágenes
        self.current_image = None
        self.current_dataset = None
        self.recorte_coords = None
        self.current_series_files = []

        # Crear interfaz
        self.create_widgets()

    def create_widgets(self):
        # Frame superior para selección de carpeta y lista de series
        self.frame_top = tk.Frame(self.root, bg="#f0f0f0", padx=10, pady=10)
        self.frame_top.pack(side=tk.TOP, fill=tk.X)

        # Botón para seleccionar la carpeta
        self.select_folder_button = tk.Button(self.frame_top, text="Seleccionar Carpeta DICOM",
                                              command=self.seleccionar_carpeta, bg="#4CAF50", fg="white",
                                              font=("Arial", 12))
        self.select_folder_button.pack(side=tk.LEFT)

        # Listbox para mostrar las series disponibles
        self.series_listbox = tk.Listbox(self.frame_top, selectmode=tk.SINGLE, height=5, font=("Arial", 12))
        self.series_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Botón para visualizar la serie seleccionada
        self.visualize_button = tk.Button(self.frame_top, text="Visualizar Serie", command=self.visualizar_serie,
                                          bg="#2196F3", fg="white", font=("Arial", 12))
        self.visualize_button.pack(side=tk.RIGHT)

        # Botón para aplicar el recorte
        self.crop_button = tk.Button(self.frame_top, text="Recorte Manual", command=self.preparar_recorte_manual,
                                     bg="#FF5722", fg="white", font=("Arial", 12))
        self.crop_button.pack(side=tk.RIGHT, padx=10)

        # Botón para visualizar imágenes recortadas
        self.view_cropped_button = tk.Button(self.frame_top, text="Visualizar Recortes",
                                             command=self.seleccionar_carpeta_recortada, bg="#009688", fg="white",
                                             font=("Arial", 12))
        self.view_cropped_button.pack(side=tk.RIGHT, padx=10)

        # Frame para contener el canvas y los scrollbars
        self.frame_canvas = tk.Frame(self.root, bg="#f0f0f0")
        self.frame_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Canvas para la visualización de las imágenes
        self.canvas = tk.Canvas(self.frame_canvas, bg="black")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Scrollbars para el Canvas
        self.scroll_x = tk.Scrollbar(self.frame_canvas, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scroll_y = tk.Scrollbar(self.frame_canvas, orient=tk.VERTICAL, command=self.canvas.yview)

        # Colocar los scrollbars
        self.scroll_x.grid(row=1, column=0, sticky="ew")
        self.scroll_y.grid(row=0, column=1, sticky="ns")

        # Configurar el canvas para trabajar con los scrollbars
        self.canvas.config(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.frame_canvas.grid_rowconfigure(0, weight=1)
        self.frame_canvas.grid_columnconfigure(0, weight=1)

        # Eventos de recorte en el Canvas
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def seleccionar_carpeta(self):
        self.dicom_folder = filedialog.askdirectory(title="Seleccione la carpeta que contiene los archivos DICOM")
        if self.dicom_folder:
            self.organizar_dicom()
            self.mostrar_series()

    def organizar_dicom(self):
        # Limpiar series anteriores
        self.dicom_files_by_series.clear()

        # Crear una carpeta de salida para almacenar las series organizadas
        output_folder = 'dicom_series_organizadas'
        os.makedirs(output_folder, exist_ok=True)

        # Obtener todos los archivos DICOM en la carpeta
        dicom_files = [os.path.join(self.dicom_folder, f) for f in os.listdir(self.dicom_folder)]

        # Iterar sobre los archivos y clasificar según la serie
        for dicom_file in dicom_files:
            try:
                dataset = pydicom.dcmread(dicom_file)
                series_number = dataset.SeriesNumber

                # Verificar si la serie ya está en el diccionario
                if dicom_file not in self.dicom_files_by_series[series_number]:
                    self.dicom_files_by_series[series_number].append((dataset.InstanceNumber, dicom_file))

                # Crear una carpeta para cada serie
                series_folder = os.path.join(output_folder, f'Serie_{series_number}')
                os.makedirs(series_folder, exist_ok=True)

                # Copiar el archivo a la carpeta de la serie correspondiente
                shutil.copy(dicom_file, series_folder)

            except Exception as e:
                print(f"No se pudo leer el archivo {dicom_file}: {e}")

    def mostrar_series(self):
        # Limpiar la lista de series
        self.series_listbox.delete(0, tk.END)

        # Agregar las series a la lista
        for series_number in sorted(self.dicom_files_by_series.keys()):
            self.series_listbox.insert(tk.END,
                                       f"Serie {series_number} ({len(self.dicom_files_by_series[series_number])} imágenes)")

    def visualizar_serie(self):
        selected_series_index = self.series_listbox.curselection()
        if not selected_series_index:
            messagebox.showwarning("Advertencia", "Debe seleccionar una serie para visualizar.")
            return

        series_number = sorted(self.dicom_files_by_series.keys())[selected_series_index[0]]
        self.current_series_files = self.dicom_files_by_series[series_number]

        # Limpiar el canvas antes de mostrar nuevas imágenes
        self.canvas.delete("all")
        self.image_refs.clear()  # Limpiar las referencias de imágenes anteriores

        # Cargar y mostrar las imágenes en el canvas
        for i, (instance_number, dicom_file) in enumerate(self.current_series_files):
            dataset = pydicom.dcmread(dicom_file)  # Aquí solo pasamos dicom_file, no una tupla
            image_array = dataset.pixel_array
            image = Image.fromarray(image_array)
            image = image.resize((150, 150))  # Redimensionar la imagen para que encaje bien en la interfaz
            image_tk = ImageTk.PhotoImage(image)

            x = (i % 5) * 160
            y = (i // 5) * 160
            self.canvas.create_image(x, y, anchor="nw", image=image_tk)
            self.canvas.create_text(x + 75, y + 140, text=f"Instancia {instance_number}", fill="white",
                                    font=("Arial", 8))

            self.image_refs.append(image_tk)  # Guardar la referencia a la imagen

        # Actualizar scroll region
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def preparar_recorte_manual(self):
        # Verificar si una serie ha sido seleccionada
        selected_series_index = self.series_listbox.curselection()
        if not selected_series_index:
            messagebox.showwarning("Advertencia", "Debe seleccionar una serie para recortar.")
            return

        # Obtener la serie seleccionada
        series_number = sorted(self.dicom_files_by_series.keys())[selected_series_index[0]]
        self.current_series_files = self.dicom_files_by_series[series_number]

        # Limpiar la visualización de las series
        self.canvas.delete("all")
        self.image_refs.clear()  # Limpiar las referencias de imágenes anteriores

        # Seleccionar la imagen central para el recorte manual
        mid_index = len(self.current_series_files) // 2
        _, dicom_file = self.current_series_files[mid_index]  # Aquí obtenemos solo el archivo
        self.current_dataset, self.current_image = cargar_imagen_dicom(dicom_file)

        if self.current_image is not None:
            self.display_image(self.current_image, 0)

    def seleccionar_carpeta_recortada(self):
        cropped_folder = filedialog.askdirectory(title="Seleccione la carpeta con las imágenes recortadas")
        if cropped_folder:
            self.mostrar_imagenes_carpeta(cropped_folder)

    def mostrar_imagenes_carpeta(self, folder_path):
        # Limpiar el canvas antes de mostrar nuevas imágenes
        self.canvas.delete("all")
        self.image_refs.clear()  # Limpiar las referencias de imágenes anteriores

        # Obtener todos los archivos en la carpeta
        dicom_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
                       os.path.isfile(os.path.join(folder_path, f))]

        # Cargar y mostrar las imágenes recortadas
        for i, dicom_file in enumerate(dicom_files):
            dataset, image_array = cargar_imagen_dicom(dicom_file)
            if image_array is not None:
                image = Image.fromarray(image_array)
                image = image.resize((150, 150))  # Redimensionar la imagen para que encaje bien en la interfaz
                image_tk = ImageTk.PhotoImage(image)

                x = (i % 5) * 160
                y = (i // 5) * 160
                self.canvas.create_image(x, y, anchor="nw", image=image_tk)
                self.canvas.create_text(x + 75, y + 140, text=f"Archivo {i + 1}", fill="white", font=("Arial", 8))

                self.image_refs.append(image_tk)  # Guardar la referencia a la imagen

        # Actualizar scroll region
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def display_image(self, image, index):
        pil_image = Image.fromarray(image)
        self.tk_image = ImageTk.PhotoImage(pil_image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.image_refs.append(self.tk_image)  # Guardar referencia de la imagen

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                    outline='red')

    def on_mouse_drag(self, event):
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y
        self.recorte_coords = (self.start_x, self.start_y, end_x, end_y)
        print(f"Área de recorte seleccionada: {self.recorte_coords}")

        # Confirmar si desea aplicar el recorte
        if messagebox.askyesno("Confirmar Recorte", "¿Estás seguro de que deseas aplicar este recorte?"):
            self.aplicar_recorte()

    def aplicar_recorte(self):
        if self.current_image is None or self.recorte_coords is None:
            messagebox.showwarning("Advertencia", "No se ha seleccionado ninguna imagen o área de recorte.")
            return

        series_number = sorted(self.dicom_files_by_series.keys())[self.series_listbox.curselection()[0]]
        files = self.dicom_files_by_series[series_number]
        output_folder = os.path.join('dicom_series_organizadas', f'Serie_{series_number}', 'recortadas')
        os.makedirs(output_folder, exist_ok=True)

        for _, dicom_file in files:  # Aquí obtenemos solo el archivo
            dataset, imagen = cargar_imagen_dicom(dicom_file)

            if imagen is not None:
                # Aplicar recorte con padding a la imagen usando las coordenadas seleccionadas
                imagen_recortada = recortar_manual(imagen, self.recorte_coords)

                # Guardar la imagen recortada con padding en la carpeta de salida
                output_file = os.path.join(output_folder, os.path.basename(dicom_file))
                guardar_imagen_recortada(dataset, imagen_recortada, output_file)

                print(f"Imagen recortada y rellenada guardada en: {output_file}")

        messagebox.showinfo("Éxito", "Las imágenes recortadas han sido guardadas exitosamente.")


# Función para cargar un archivo DICOM y convertirlo a una matriz numpy
def cargar_imagen_dicom(dicom_file):
    try:
        dataset = pydicom.dcmread(dicom_file)
        imagen = dataset.pixel_array
        return dataset, imagen
    except Exception as e:
        print(f"Error al leer el archivo {dicom_file}: {e}")
        return None, None


# Función de recorte con padding
def recortar_manual(imagen, recorte_coords):
    x1, y1, x2, y2 = recorte_coords
    recorte = imagen[int(y1):int(y2), int(x1):int(x2)]

    # Dimensiones originales
    original_height, original_width = imagen.shape

    # Dimensiones del recorte
    recorte_height, recorte_width = recorte.shape

    # Crear una imagen nueva con el tamaño original y rellenada con ceros (negro)
    imagen_con_padding = np.zeros((original_height, original_width), dtype=imagen.dtype)

    # Calcular la posición para centrar el recorte en la nueva imagen
    start_y = (original_height - recorte_height) // 2
    start_x = (original_width - recorte_width) // 2

    # Colocar el recorte en la imagen con padding
    imagen_con_padding[start_y:start_y + recorte_height, start_x:start_x + recorte_width] = recorte

    return imagen_con_padding


# Función para guardar la imagen recortada
def guardar_imagen_recortada(dataset, imagen_recortada, output_file):
    dataset.PixelData = imagen_recortada.tobytes()
    dataset.Rows, dataset.Columns = imagen_recortada.shape
    dataset.save_as(output_file)


if __name__ == "__main__":
    root = tk.Tk()
    app = DICOMViewerApp(root)
    root.mainloop()
