import math
import numpy
import decimal
import os

class action_file:
  def __init__(self, open_file_path, result_file_path, file_name):
    # 변수 초기화
    self.open_file_path = open_file_path
    self.result_file_path = result_file_path
    self.file_name = file_name
    
    # 첫번째 줄을 제외했나?, 추출했나?
    self.is_first = False
    # 첫번째(값의 이름)을 출력했나?
    self.is_title = False
    # 루트 값을 출력할 건가?
    self.is_print_rt = True

    self.title = ""

    self.vg_rt_id_arr = []
    self.arr_x = []
    self.arr_y = []

    self.arr_values = []

    self.slope = 0

    self.ori_vg = 0
    self.ori_id = 0
    self.ori_ig = 0

    self.ab_id = 0
    self.ab_ig = 0

    self.rt_id = 0

    self.avg_x = 0
    self.avg_y = 0

    self.inter_y = 0
    self.inter_x = 0
    self.mob = 0
    self.W = 0
    self.L = 0
    self.C = 0

  def start(self, L, W, C, FV, point_count, is_n_type):
    self.open_file()

    while True:
      line = self.file_ori.readline()

      # 타이틀 설정
      if not self.is_first:
        self.set_title(line)
        continue
      
      # 빈줄이면 끝남
      if not line:
        break

      # 값 추출하기
      arr = self.get_values(line)

      # 문자열 만들기
      text = self.get_strs(arr)

      # N 타입인가 아닌가 구분
      if not is_n_type:  
        if self.ori_vg <= FV and self.is_print_rt:
          self.calculate(W, L, C, point_count)
          self.append_caculated_values(W, L, C)
      else:
        if self.ori_vg >= FV and self.is_print_rt:
          self.calculate(W, L, C, point_count)
          self.append_caculated_values(W, L, C)
      
      if not self.is_title:
        self.output_title_to_file()

      self.arr_values.append(text)

    for txt in self.arr_values:
      self.output_to_file(txt)
    
    self.close_file()

  def open_file(self):
    self.file_ori = open(self.open_file_path, 'r')
    self.file_result = open(self.result_file_path, 'w')

  def set_title(self, line):
    self.is_first = True
    axis = line.split(',')
    axis[15] = axis[15].replace('\n', '')
    self.title = axis[14] + ',' + axis[13] + ',' + axis[15] + ',,' + axis[14] + ',absID,absIG,RootID,,' + 'file name,' + 'slope,intercept,Vth'\
       + ',mobility,' + 'Width,' + 'Length,' + 'Capacitance\n'

  def get_values(self, line):
    # 값 추출
    arr = line.split(',')

    arr[15] = arr[15].replace('\n','')

    self.ori_vg = int(arr[14])
    self.ori_id = decimal.Decimal(arr[13])
    self.ori_ig = decimal.Decimal(arr[15])

    self.ab_id = abs(self.ori_id)
    self.ab_ig = abs(self.ori_ig)

    self.rt_id = math.sqrt(self.ab_id)

    self.vg_rt_id_arr.append([self.ori_vg, self.rt_id])

    return arr

  def get_strs(self, arr):
    # 값 문자열 만들기
    text = ""
    
    if not self.is_print_rt:
      text = arr[14] + "," + arr[13] + "," + arr[15] + ",," + str(self.ori_vg) + "," + str(self.ab_id) + "," + str(self.ab_ig) + "\n"
    else:
      text = arr[14] + "," + arr[13] + "," + arr[15] + ",," + str(self.ori_vg) + "," + str(self.ab_id) + "," + str(self.ab_ig) + "," + str(self.rt_id) + "\n"

    return text

  def calculate(self, W, L, C, point_count):
    self.is_print_rt = False

    # 기울기 구하기
    for i in range(len(self.vg_rt_id_arr) - point_count, len(self.vg_rt_id_arr)):
      tmp = self.vg_rt_id_arr[i]
      self.arr_x.append(tmp[0])
      self.arr_y.append(tmp[1])

    self.avg_x = numpy.mean(numpy.array(self.arr_x))
    self.avg_y = numpy.mean(numpy.array(self.arr_y))

    son = []
    mom = []

    for i in range(0, len(self.arr_x)):
      son.append((self.arr_x[i] - self.avg_x) * (self.arr_y[i] - self.avg_y))
      mom.append(pow(self.arr_x[i] - self.avg_x, 2))

    son_val = numpy.sum(numpy.array(son))
    mom_val = numpy.sum(numpy.array(mom))

    self.slope = son_val / mom_val

    self.inter_y = self.avg_y - self.slope * self.avg_x
    self.inter_x = (-self.inter_y) / self.slope

    self.mob = pow(self.slope, 2) * ((2 * L) / W) * (1 / C)

    self.W = W
    self.L = L
    self.C = C

  def append_caculated_values(self, W, L, C):
    tmp = self.arr_values[0]    
    self.arr_values[0] = str(tmp).replace('\n', '') + ',,'+ self.file_name + ',' + str(self.slope) +','\
     + str(self.inter_x) + ',' + str(self.inter_y) + ',' + str(self.mob) +',' + str(W) + ',' + str(L) + ',' + str(C) + '\n'

  def output_title_to_file(self):
    self.is_title = True
    self.file_result.write(self.title)

  def output_to_file(self, text):
    self.file_result.write(text)

  def close_file(self):
    self.file_ori.close()
    self.file_result.close()

  def get_results(self):
    return [self.file_name, self.slope, self.inter_y, self.inter_x, self.mob, self.W, self.L, self.C]

class system:
  def __init__(self, main):
    self.L = 100
    self.W = 1000
    self.C = 4.44E-08
    self.FV = -40
    self.point_count = 5
    self.is_n_type = False
    self.main = main

  def start(self, folder_path, result_folder_path):
    try:
      file_list = os.listdir(folder_path)
      file_list_csv = [file for file in file_list if file.endswith('.csv')]
      result_list = []

      for file_path in file_list_csv:
        file = action_file(folder_path + '/' + file_path, result_folder_path + '/' + file_path, file_path)
        file.start(self.get_L(), self.get_W(), self.get_C(), self.get_FV(), self.get_point_count(), self.get_is_n_type())
        result_list.append(file.get_results())

      self.create_result_list_file(result_list, result_folder_path)
      return True
    except IndexError as e:
      print(e)
      self.main.error('N 타입 여부 또는 FV를 다시 설정하세요.')
      return False
    except PermissionError as e:
      print(e)
      self.main.error('작업 파일이 열려있어요.')
      return False

  def create_result_list_file(self, result_list, result_folder_path):
    file = open(result_folder_path + '/mobility.csv', 'w')
    file.write('file name,slope,intercept,Vth,mobility,Width,Length,Capacitance\n')

    for item in result_list:
      text = F'{item[0]},{item[1]},{item[2]},{item[3]},{item[4]},{item[5]},{item[6]},{item[7]}'
      file.write(text + '\n')

    file.close()

  def get_W(self):
    return self.W
  
  def get_L(self):
    return self.L

  def get_C(self):
    return self.C
  
  def get_FV(self):
    return self.FV
  
  def get_point_count(self):
    return self.point_count

  def get_is_n_type(self):
    return self.is_n_type
  
  def set_W(self, W):
    self.W = W
  
  def set_L(self, L):
    self.L = L

  def set_C(self, C):
    self.C = C
  
  def set_FV(self, FV):
    self.FV = FV

  def set_point_count(self, point_count):
    self.point_count = point_count

  def set_is_n_type(self, value):
    self.is_n_type = value