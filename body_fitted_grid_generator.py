# coding: utf-8
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import bicg, spsolve
from math import floor
from scipy import interpolate
import numpy as np
from naca_4digit_test import Naca_4_digit, Naca_5_digit
from joukowski_wing import joukowski_wing_complex, karman_trefftz_wing_complex
import matplotlib.pyplot as plt

# 物体表面の複素座標を取得する
def get_complex_coords(type, size, center_x = -0.08, center_y = 0.08, naca4 = "0012"):
    def reshape_z(z):
        if z[0] != z[z.shape[0] - 1]:
            return np.concatenate([z, z[0].reshape(-1)]), z.shape[0] + 1
        else:
            return z, z.shape[0]
    
    # 極端に距離の近い制御点を除去する
    def adjust_length(z):
        len = np.zeros_like(z, dtype = float)
        len[:z.shape[0] - 1] = np.abs(z[1:] - z[:z.shape[0] - 1])
        len[z.shape[0] - 1] = np.abs(z[0] - z[z.shape[0] - 1])
        average_len = np.average(len)

        put_out = lambda x, count: np.hstack((x[:count], x[count + 1]))
        count = z.shape[0] - 2
        while count > 0:
            if len[count] < 0.1 * average_len:
                z = put_out(z, count)
            count -= 1
        return z

    if type == 0:
        t = np.linspace(start = 0, stop = 2.0 * np.pi, num = size + 1)
        z = np.exp(1j * t)[:size]
    elif type == 1:
        z = joukowski_wing_complex(size, center_x, center_y)
    elif type == 2:
        z = karman_trefftz_wing_complex(size, center_x, center_y)
    elif type == 3:
        naca = Naca_4_digit(int_4 = naca4, attack_angle_deg = 0.0, resolution = size, quasi_equidistant = False)
        z = naca.transform2complex()
    elif type == 4:
        naca = Naca_5_digit(int_5 = naca4, attack_angle_deg = 0.0, resolution = size, quasi_equidistant = False,
                            length_adjust = True)
        z = naca.transform2complex()
    else:
        print("type error")
        exit()
    
    z = adjust_length(z)
    if type < 3:
        return reshape_z(z)
    else:
        return z, z.shape[0]



# 格子の外部境界(分割数は物体と同じの，物体形状の長軸長さのmagnification倍の円を返す)
def get_outer_boundary(z1, magnification=5):
    # 物体の代表長さを得る(x,y方向どちらかが最大と仮定しており，最長部長さを求めているわけでないことに注意されたし)
    def get_model_length(z):
        def get_length(x):
            return np.max(x) - np.min(x)

        x = np.real(z)
        y = np.real(z)
        return max(get_length(x), get_length(y))

    # 物体の中心位置を返す
    def get_model_center(z):
        return np.average(np.real(z)), np.average(np.imag(z))

    model_length = get_model_length(z1)
    center_x, center_y = get_model_center(z1)
    zc = center_x + 1j * center_y
    radius = model_length * magnification

    # 法線の角度
    delta2 = get_delta2(z1)
    theta1 = np.angle(delta2 / (np.abs(delta2) * 1j))
    theta1 = np.where(theta1 > 0, theta1, theta1 + 2.0 * np.pi)

    # 物体を円に変換したときの換算角度
    theta2 = get_length_rate(z1) * 2.0 * np.pi
    average_theta = np.sort(0.5 * (theta1 + theta2))
    z3 = zc + radius * np.exp(1j * average_theta)
    return z3[::-1] # Clock Wise and -1

# そこまでの累積長さが全体の長さに占める割合を返す
def get_length_rate(z1, output_total_length = False):
    size = z1.shape[0]
    delta1 = np.zeros_like(z1, dtype = complex)
    delta1[:size - 1] = z1[1:] - z1[:size - 1]
    delta1[size - 1] = z1[0] - z1[size - 1]
    len = np.abs(delta1)
    total_len = np.sum(len)
    len_rate = np.zeros_like(z1, dtype = float)
    accumulated_len = 0.0
    for i in range(size):
        len_rate[i] = accumulated_len / total_len
        accumulated_len += len[i]
    if output_total_length:
        return len_rate, total_len
    else:
        return len_rate

# 1点飛ばしでの座標の差分を返す
def get_delta2(z1):
    size = z1.shape[0]
    delta2 = np.zeros_like(z1, dtype = complex)
    delta2[0] = z1[1] - z1[size - 1]
    for i in range(1, size - 1):
        delta2[i] = z1[i + 1] - z1[i - 1]
    delta2[size - 1] = z1[0] - z1[size - 2]
    return delta2

# 物体と外周を結ぶ線分を返す
def get_connect_z1_to_z3(z1, z3, resolution=None, magnification=10):
    if resolution == None:
        resolution = z1.shape[0]
    else:
        resolution = resolution

    inner_end = z1[np.argmax(np.real(z1))]  # 内側のx方向最大位置
    outer_end = z3[np.argmax(np.real(z3))]  # 外側のx方向最大位置

    exp_end = np.log(magnification) # 指定倍率:magnificationに達する指数関数上の位置:magnification = exp(exp_end) + 1

    delta_x = np.exp(np.linspace(0, exp_end, resolution - 2, dtype=complex))    # 指数関数の等間隔サンプリング
    raw_length = np.sum(delta_x)    # 等間隔サンプリングされた微小長さの総和
    delta_x = (outer_end - inner_end) / raw_length * delta_x # 内から外への長さにスケーリング&方向を付ける

    z2 = np.zeros(resolution, dtype=complex)
    z2[0] = inner_end
    z2[resolution - 1] = outer_end
    for k in range(1, resolution-1):
        z2[k] = z2[k-1] + delta_x[k - 1]

    return z2
    
def deduplication(z, array_list=None):
    def put_out(x, count):
        return np.hstack((x[:count], x[count+1]))

    def put_out_bound(x):
        return x[:x.shape[0] - 1]
        
    size = z.shape[0]
    
    if z[size - 1] == z[0]:
        size -= 1
        z = put_out_bound(z)
        if array_list != None:
            for i in range(len(array_list)):
                array_list[i] = put_out_bound(array_list[i])
    
    count = size - 2
    while count > 0:
        if z[count] == z[count + 1]:
            z = put_out(z, count)
            if array_list != None:
                for i in range(len(array_list)):
                    array_list[i] = put_out(array_list[i], count)
        count -= 1
    if array_list == None:
        return z
    else:
        return z, array_list

def redistribute(z1, deterring_concentration_number = 2):
    # エルミート補間して関数x=fx(t), y=fy(t)を得る
    t, total_len = get_length_rate(z1, output_total_length = True)

    fx = interpolate.PchipInterpolator(np.hstack((t, np.array([1.0]))), np.real(np.hstack((z1, z1[0]))))
    fy = interpolate.PchipInterpolator(np.hstack((t, np.array([1.0]))), np.imag(np.hstack((z1, z1[0]))))
    size = z1.shape[0]

    # 隣接2辺がなす角度の直線からのずれ量を算出
    delta = np.zeros_like(z1, dtype = complex)
    delta[0] = (z1[0] - z1[size - 1])
    delta[1:] = (z1[1:] - z1[:size - 1])
    len = np.abs(delta)
    unit_delta = delta / len
    angle = np.zeros_like(z1, dtype = float)
    angle[:size - 1] = np.angle(unit_delta[1:] / (-unit_delta[:size - 1]))
    angle[size - 1] = np.angle(unit_delta[0] / (-unit_delta[size - 1]))
    angle = np.where(angle >= 0, angle, angle + 2.0 * np.pi)

    res_angle = np.abs(angle - np.pi)
    # 辺の中心におけるずれ量を定義
    res_angle_edge = 0.5 * np.hstack(((res_angle[1:] + res_angle[:res_angle.shape[0] - 1]), np.array(res_angle[0] - res_angle[res_angle.shape[0] - 1])))
    # ずれ量を格子点数で規格化/整数値で分割できるように分配
    tmp_num = res_angle_edge / np.sum(res_angle_edge) * size
    num = np.zeros_like(tmp_num, dtype=int)
    res = 0.0
    for i in range(size):
        res += tmp_num[i] - floor(tmp_num[i])
        if res < 1.0:
            num[i] = floor(tmp_num[i])
        else:
            num[i] = floor(tmp_num[i]) + 1
            res -= 1.0

    if np.sum(num) != size:
        num[size - 1] += 1
    # 点の集中し過ぎを防ぐため初期長さの半分を最小値として分配数調整
    flag = 0
    dcn = deterring_concentration_number

    while flag == 0:
        flag = 1
        if num[0] > dcn:
            num[0] -= 1
            if num[1] > dcn:
                num[size - 1] += 1
            else:
                num[1] += 1
            flag = 0

        for i in range(1, size - 1):
            if num[i] > dcn:
                num[i] -= 1
                if num[i + 1] > dcn:
                    num[i - 1] += 1
                else:
                    num[i + 1] += 1
                flag = 0

        if num[size - 1] > dcn:
            num[size - 1] -= 1
            if num[0] > dcn:
                num[size - 2] += 1
            else:
                num[0] += 1
            flag = 0

    # 点を配置
    d_len = np.hstack((t, np.array(1.0)))
    d_len = d_len[1:] - d_len[:d_len.shape[0] - 1]

    previous_t = 0.0
    new_t = np.zeros_like(t)
    k = 1
    for i in range(size):
        if num[i] != 0:
            for j in range(num[i]):
                new_t[k] = previous_t + d_len[i] / num[i]
                previous_t = new_t[k]
                k += 1
                if k == size:
                    break
        else:
            previous_t += d_len[i]

    t = new_t

    z1 = fx(t) + 1j * fy(t)
    return z1




def make_grid_seko(z1):
    z1 = redistribute(z1)
    z3 = get_outer_boundary(z1, magnification=5)
    z2 = get_connect_z1_to_z3(z1, z3)
    xi_max = z1.shape[0]
    eta_max = z2.shape[0]
    
    grid_x = np.zeros((xi_max, eta_max))
    grid_y = np.zeros((xi_max, eta_max))
    grid_x[:, 0] = np.real(z1)
    grid_y[:, 0] = np.imag(z1)
    grid_x[:, eta_max - 1] = np.real(z3[::-1])
    grid_y[:, eta_max - 1] = np.imag(z3[::-1])
    
    for j in range(1, eta_max-1):
        grid_x[:, j] = (1.0 - float(j) / eta_max) * grid_x[:, 0] + (float(j) / eta_max) * grid_x[:, eta_max - 1]
        grid_y[:, j] = (1.0 - float(j) / eta_max) * grid_y[:, 0] + (float(j) / eta_max) * grid_y[:, eta_max - 1]

    def x_xi(i, j):
        if i == 0:
            return 0.5 * (grid_x[1, j] - grid_x[xi_max - 1, j]) # loop boundary
        elif i == xi_max - 1:
            return 0.5 * (grid_x[0, j] - grid_x[xi_max - 2, j])
        else:
            return 0.5 * (grid_x[i+1, j] - grid_x[i-1, j])
        
    def y_xi(i, j):
        if i == 0:
            return 0.5 * (grid_y[1, j] - grid_y[xi_max - 1, j])  # loop boundary
        elif i == xi_max - 1:
            return 0.5 * (grid_y[0, j] - grid_y[xi_max - 2, j])
        else:
            return 0.5 * (grid_y[i+1, j] - grid_y[i-1, j])
        
    def x_eta(i, j):
        if j == 0:
            return 0.5 * (-grid_x[i, 2] + 4.0 * grid_x[i, 1] - 3.0 * grid_x[i, 0])
        elif j == eta_max - 1:
            return - 0.5 * (-grid_x[i, eta_max - 3] + 4.0 * grid_x[i, eta_max - 2] - 3.0 * grid_x[i, eta_max - 1])
        else:
            return 0.5 * (grid_x[i, j+1] - grid_x[i, j-1])
        
    def y_eta(i, j):
        if j == 0:
            return 0.5 * (-grid_y[i, 2] + 4.0 * grid_y[i, 1] - 3.0 * grid_y[i, 0])
        elif j == eta_max - 1:
            return - 0.5 * (-grid_y[i, eta_max - 3] + 4.0 * grid_y[i, eta_max - 2] - 3.0 * grid_y[i, eta_max - 1])
        else:
            return 0.5 * (grid_y[i, j+1] - grid_y[i, j-1])
    
    def x_xixi(i, j):
        if i == 0:
            return grid_x[1, j] - 2.0 * grid_x[0, j] + grid_x[xi_max-1, j]
        elif i == xi_max - 1:
            return grid_x[0, j] - 2.0 * grid_x[xi_max-1, j] + grid_x[xi_max-2, j]
        else:
            return grid_x[i+1, j] - 2.0 * grid_x[i, j] + grid_x[i-1, j]
            
    def y_xixi(i, j):
        if i == 0:
            return grid_y[1, j] - 2.0 * grid_y[0, j] + grid_y[xi_max-1, j]
        elif i == xi_max - 1:
            return grid_y[0, j] - 2.0 * grid_y[xi_max-1, j] + grid_y[xi_max-2, j]
        else:
            return grid_y[i+1, j] - 2.0 * grid_y[i, j] + grid_y[i-1, j]
    
    def x_etaeta(i, j):
        if j == 0:
            return 2.0 * grid_x[i, 0] - 5.0 * grid_x[i, 1] + 4.0 * grid_x[i, 2] - grid_x[i, 3]
        elif j == eta_max - 1:
            return -(2.0 * grid_x[i, eta_max-1] - 5.0 * grid_x[i, eta_max-2] + 4.0 * grid_x[i, eta_max-3] - grid_x[i, eta_max-4])
        else:
            return grid_x[i, j+1] - 2.0 * grid_x[i, j] + grid_x[i, j-1]

    def y_etaeta(i, j):
        if j == 0:
            return 2.0 * grid_y[i, 0] - 5.0 * grid_y[i, 1] + 4.0 * grid_y[i, 2] - grid_y[i, 3]
        elif j == eta_max - 1:
            return -(2.0 * grid_y[i, eta_max-1] - 5.0 * grid_y[i, eta_max-2] + 4.0 * grid_y[i, eta_max-3] - grid_y[i, eta_max-4])
        else:
            return grid_y[i, j+1] - 2.0 * grid_y[i, j] + grid_y[i, j-1]

    def x_xieta(i, j):
        if i == 0:
            i_l = xi_max - 1
            i_r = 1
        elif i == xi_max - 1:
            i_l = xi_max - 2
            i_r = 0
        else:
            i_l = i - 1
            i_r = i + 1
        
        if j == 0:
            return 0.25 * ((-grid_x[i_r, 2] + 4.0*grid_x[i_r, 1] - 3.0 * grid_x[i_r, 0])
                           - (-grid_x[i_l, 2] + 4.0*grid_x[i_l, 1] - 3.0 * grid_x[i_l, 0]))
        elif j == eta_max - 1:
            return -0.25 * ((-grid_x[i_r, eta_max-3] + 4.0*grid_x[i_r, eta_max-2] - 3.0 * grid_x[i_r, eta_max-1])
                           - (-grid_x[i_l, eta_max-3] + 4.0*grid_x[i_l, eta_max-2] - 3.0 * grid_x[i_l, eta_max-1]))
        else:
            return 0.5 * (
                grid_x[i_r, j + 1] - grid_x[i_r, j] - grid_x[i, j + 1] + 2.0 * grid_x[i, j] - grid_x[i, j - 1] -
                grid_x[i_l, j] + grid_x[i_l, j - 1])

    def y_xieta(i, j):
        if i == 0:
            i_l = xi_max - 1
            i_r = 1
        elif i == xi_max - 1:
            i_l = xi_max - 2
            i_r = 0
        else:
            i_l = i - 1
            i_r = i + 1
    
        if j == 0:
            return 0.25 * ((-grid_y[i_r, 2] + 4.0 * grid_y[i_r, 1] - 3.0 * grid_y[i_r, 0])
                           - (-grid_y[i_l, 2] + 4.0 * grid_y[i_l, 1] - 3.0 * grid_y[i_l, 0]))
        elif j == eta_max - 1:
            return -0.25 * (
                        (-grid_y[i_r, eta_max - 3] + 4.0 * grid_y[i_r, eta_max - 2] - 3.0 * grid_y[i_r, eta_max - 1])
                        - (-grid_y[i_l, eta_max - 3] + 4.0 * grid_y[i_l, eta_max - 2] - 3.0 * grid_y[i_l, eta_max - 1]))
        else:
            return 0.5 * (
                    grid_y[i_r, j + 1] - grid_y[i_r, j] - grid_y[i, j + 1] + 2.0 * grid_y[i, j] - grid_y[i, j - 1] -
                    grid_y[i_l, j] + grid_y[i_l, j - 1])

    g11 = lambda i, j: x_xi(i, j)**2 + y_xi(i, j)**2
    g12 = lambda i, j: x_xi(i, j) * x_eta(i, j) + y_xi(i, j) * y_eta(i, j)
    g22 = lambda i, j: x_eta(i, j)**2 + y_eta(i, j)**2
    
    # xi線をxi0線へ近づける制御関数P
    def control_function_of_xi(xi, eta, xi_line, eta_line, a=1.0, b=0.0, c=1.0, d=0.0,  not_move_xi=True):
        if (eta != 1) and (eta != eta_max - 2):
            if not_move_xi:
                return 0
            else:
                p = 0
                for xi0 in xi_line:
                    p += - a * np.sign(xi - xi0) * np.exp(-c * np.abs(xi - xi0))
                return p
        else:
            i = xi
            j = eta
            return -(-(x_xi(i, j) * x_xixi(i, j) + y_xi(i, j) * y_xixi(i, j)) / g11(i, j)
                    -(x_xi(i, j) * x_etaeta(i, j) + y_xi(i, j) * y_etaeta(i, j)) / g22(i, j))
        
    # eta線をeta0線へ近づける制御関数Q
    def control_function_of_eta(xi, eta, xi_line, eta_line, a=1.0, b=0.0, c=1.0, d=0.0):
        if (eta != 1) and (eta != eta_max - 2):
            q = 0
            for eta0 in eta_line:
                q += - a * np.sign(eta - eta0) * np.exp(-c * np.abs(eta - eta0))
            return q
        else:
            i = xi
            j = eta
            return -(-(x_eta(i, j) * x_etaeta(i, j) + y_eta(i, j) * y_etaeta(i, j)) / g22(i, j)
                    -(x_eta(i, j) * x_xixi(i, j) + y_eta(i, j) * y_xixi(i, j)) / g11(i, j))
    
    def update_control_function(xi_line = [0], eta_line = [0], not_move_xi = True):
        for i in range(xi_max):
            for j in range(eta_max):
                control_P[i, j] = control_function_of_xi(i, j, xi_line, eta_line)
                control_Q[i, j] = control_function_of_eta(i, j, xi_line, eta_line)
        return control_P, control_Q
    
    # explicit euler (for check)
    control_P = np.zeros((xi_max, eta_max))
    control_Q = np.zeros((xi_max, eta_max))
    
    
    def rhs_x(i, j):
        if (j != 1) and (j != eta_max-2):
            return ((g22(i, j) * (x_xixi(i, j) + control_P[i, j] * x_xi(i, j)))
                    + (g11(i, j) * (x_etaeta(i, j) + control_Q[i, j] * x_eta(i, j)))
                    - 2.0 * g12(i, j) * x_xieta(i, j))
        else:
            return (g22(i, j) * x_xixi(i, j) + control_P[i, j] * x_xi(i, j)
                    + g11(i, j) * x_etaeta(i, j) + control_Q[i, j] * x_eta(i, j))
    
    def rhs_y(i, j):
        if (j != 1) and (j != eta_max - 2):
            return ((g22(i, j) * (y_xixi(i, j) + control_P[i, j] * y_xi(i, j)))
                    + (g11(i, j) * (y_etaeta(i, j) + control_Q[i, j] * y_eta(i, j)))
                    - 2.0 * g12(i, j) * y_xieta(i, j))
        else:
            return (g22(i, j) * y_xixi(i, j) + control_P[i, j] * y_xi(i, j)
                    + g11(i, j) * y_etaeta(i, j) + control_Q[i, j] * y_eta(i, j))

    def sample_output_vtk(place="Lab"):
        fname = "sample.vtk"
        with open(fname, 'w') as f:
            point_number = str(xi_max * eta_max)
            cell_number = str((xi_max) * (eta_max - 1))
            cell_vertex_number = str(5 * (xi_max) * (eta_max - 1))
            pid = lambda i, j: i + eta_max * j
            
            def cell_structure(i, j):
                if i != xi_max - 1:
                    return "4 " + str(pid(i, j)) + " " + str(pid(i + 1, j)) + " " + str(
                        pid(i + 1, j + 1)) + " " + str(pid(i, j + 1))
                else:
                    return "4 " + str(pid(i, j)) + " " + str(pid(0, j)) + " " + str(
                        pid(0, j + 1)) + " " + str(pid(i, j + 1))
            
            # header
            f.write("# vtk DataFile Version 3.0\n")
            f.write("Unstructured Grid example\n")
            f.write("ASCII\nDATASET UNSTRUCTURED_GRID\n")
            f.write("POINTS " + point_number + " float\n")
            # point coordinates
            for j in range(eta_max):
                for i in range(xi_max):
                    f.write(str(grid_x[i, j]) + " " + str(grid_y[i, j]) + " 0.0\n")

            # cell structure
            f.write("CELLS " + cell_number + " " + cell_vertex_number + "\n")
            for j in range(eta_max - 1):
                for i in range(xi_max):
                    f.write(cell_structure(i, j) + "\n")

            # cell types
            f.write("CELL_TYPES " + cell_number + "\n")
            for j in range(eta_max - 1):
                for i in range(xi_max):
                    f.write("9\n")
    
    def plot_tmp():
        for i in range(xi_max):
            plt.plot(grid_x[i, :], grid_y[i, :])
        for j in range(eta_max):
            plt.plot(grid_x[:, j], grid_y[:, j])
        plt.xlim(-0.1, 1.1)
        plt.ylim(-0.1, 1.1)
        plt.show()
        for i in range(xi_max):
            plt.plot(grid_x[i, :], grid_y[i, :])
        for j in range(eta_max):
            plt.plot(grid_x[:, j], grid_y[:, j])
        plt.show()

    # 物体表面を押し出す
    def offset_surface(z):
        size = z.shape[0]
    
        delta = np.zeros(size, dtype = complex)
        delta[0] = z[1] - z[size - 1]
        for i in range(1, size - 1):
            delta[i] = z[i + 1] - z[i - 1]
        delta[size - 1] = z[1] - z[size - 2]

        normal = -1j * delta / np.abs(delta)
        incremental = np.min(np.abs(delta))
        return z + normal * incremental
    
    # explicit euler (gauss-seidel)
    def explicit_euler():
        dt = 0.0005
        xi_line = [0, int(eta_max/2)]
        eta_line = [0]
        # orthogonal grid line for eta = 1
        z1_eta1 = offset_surface(z1)
        grid_x[:, 1] = np.real(z1_eta1)
        grid_y[:, 1] = np.imag(z1_eta1)

        trial = 0.9
        while trial > 0:
            dt *= trial
            for iter in range(1000):
                control_P, control_Q = update_control_function(xi_line, eta_line)
                for i in range(xi_max):
                    for j in range(2, eta_max - 1):
                        grid_x[i, j] += rhs_x(i, j) * dt
                        grid_y[i, j] += rhs_y(i, j) * dt

            sample_output_vtk()
            if np.average(grid_y[:, 2] - grid_y[:, 1]) < 1.2 * np.average(grid_y[:, 1] - grid_y[:, 0]):
                trial = 0
            # plot_tmp()

        
        return grid_x, grid_y

    grid_x, grid_y = explicit_euler()
    # alternative direction implicit
    delta_tau = 0.005
    # xi方向の行列を解く
    def solve_first_matrix():
        dx_star2 = np.zeros((xi_max, eta_max))
        dy_star2 = np.zeros((xi_max, eta_max))

        for j in range(1, eta_max-1):
            matrix1 = lil_matrix((xi_max, xi_max))
            rhs1_x = np.zeros(xi_max)
            rhs1_y = np.zeros(xi_max)
            for i in range(xi_max):
                matrix1[i, i] = 1.0 + 2.0 * delta_tau * g22(i, j)
                # xi方向は周期境界となるため隅に値を置く
                if i != 0:
                    im1 = i - 1
                else:
                    im1 = xi_max - 1
                
                if i != xi_max - 1:
                    ip1 = i + 1
                else:
                    ip1 = 0
                    
                matrix1[i, im1] = -delta_tau * g22(i, j) * (1.0 - 0.5 * control_P[i, j])
                matrix1[i, ip1] = -delta_tau * g22(i, j) * (1.0 + 0.5 * control_P[i, j])

                rhs1_x[i] = rhs_x(i, j)
                rhs1_y[i] = rhs_y(i, j)

            matrix1 = matrix1.tocsr()
            dx_star2[:, j] = spsolve(matrix1, rhs1_x)
            dy_star2[:, j] = spsolve(matrix1, rhs1_y)
        return dx_star2, dy_star2

    # eta方向の行列を解く
    def solve_second_matrix(dx_star2, dy_star2):
        dx_star1 = np.zeros((xi_max, eta_max))
        dy_star1 = np.zeros((xi_max, eta_max))
        for i in range(xi_max):
            matrix2 = lil_matrix((eta_max, eta_max))
            for j in range(eta_max):
                # eta方向は等温境界
                if (j == 0) or (j == eta_max - 1):
                    matrix2[j, j] = 1.0
                else:
                    matrix2[j, j] = 1.0 + 2.0 * delta_tau * g11(i, j)
                    
                    if j != 1:
                        matrix2[j, j - 1] = -delta_tau * g11(i, j) * (1.0 - 0.5 * control_Q[i, j])
                
                    if j != eta_max - 2:
                        matrix2[j, j + 1] = -delta_tau * g11(i, j) * (1.0 + 0.5 * control_Q[i, j])

            matrix2 = matrix2.tocsr()
            dx_star1[i, :] = spsolve(matrix2, dx_star2[i, :])
            dy_star1[i, :] = spsolve(matrix2, dy_star2[i, :])
        return dx_star1, dy_star1
            
    def solve_third_matrix(dx_star1, dy_star1):
        matrix3 = lil_matrix((xi_max * eta_max, xi_max * eta_max))
        total_elements = xi_max * eta_max
        for j in range(eta_max):
            for i in range(xi_max):
                k = i + eta_max * j
                matrix3[k, k] = 1.0
                if (j != 0) and (j != eta_max - 1):
                    side_element = 0.5 * delta_tau * g12(i, j)
                    # left side
                    if j != 1:
                        if i >= 1:
                            jNlm1 = k - eta_max - 1
                        else:
                            jNlm1 = k - 1
                        matrix3[k, jNlm1] = side_element

                        if i <= xi_max - 2:
                            jNlp1 = k - eta_max + 1
                        else:
                            jNlp1 = k - 2 * eta_max + 1
                        matrix3[k, jNlp1] = - side_element

                    if j != eta_max - 2:
                        if i >= 1:
                            jNrm1 = k + eta_max - 1
                        else:
                            jNrm1 = k + 2 * eta_max - 1
                        matrix3[k, jNrm1] = - side_element

                        if i <= xi_max - 2:
                            jNrp1 = k + eta_max + 1
                        else:
                            jNrp1 = k + 1
                        matrix3[k, jNrp1] = side_element

        matrix3 = matrix3.tocsr()

        dx = spsolve(matrix3, dx_star1.T.reshape(-1))
        dy = spsolve(matrix3, dy_star1.T.reshape(-1))
        return dx.reshape(eta_max, xi_max).T, dy.reshape(eta_max, xi_max).T
            
    for i in range(10):
        xi_line = []#[0, int(eta_max/2)]
        eta_line = []#[0]
        # control_P, control_Q = update_control_function(xi_line, eta_line)

        dx_star2, dy_star2 = solve_first_matrix()
        dx_star1, dy_star1 = solve_second_matrix(dx_star2, dy_star2)
        dx, dy = solve_third_matrix(dx_star1, dy_star1)
        grid_x += dx
        grid_y += dy
        res = np.sum(np.abs(dx) + np.abs(dy))
        print(res)
        plot_tmp()
                
                        

def main():
    z1, size = get_complex_coords(type = 3, naca4 = "4912", size = 100)
    z1 = deduplication(z1)
    # z1 = np.hstack((z1[:size - 2], z1[size - 1]))
    """
    box = 10
    z1 = np.zeros(box) + 1j * np.arange(box)    #
    z2 = np.arange(box) + 1j * np.zeros(box)
    z3 = np.ones(box) * (box-1) + 1j * np.arange(box)
    z4 = np.arange(box) + 1j * np.ones(box) * (box-1)
    #"""
    """
    plt.plot(np.real(z1), np.imag(z1))
    plt.plot(np.real(z2), np.imag(z2), "o")
    plt.plot(np.real(z3), np.imag(z3), "x")
    plt.plot(np.real(z4), np.imag(z4))
    plt.show()
    """
    make_grid_seko(z1)
    plt.plot(np.real(z1), np.imag(z1))
    plt.show()

    exit()
    """
    grid[0] = line_up_z2xy(z1[:size-1], two_rows = True)
    
    xy0 = line_up_z2xy(offset_surface(z1)[:size-1])
    
    
    # print(xy0)
    phi0 = np.zeros(size-1)
    phi1 = np.zeros(size-1)
    V0 = np.zeros(size-1) + 0.0001
    V1 = np.zeros(size-1)
    cM, cV = made_coefficient_matrix(xy0[0::2], grid[0, :, 0], xy0[1::2], grid[0, :, 1], phi0, phi1, V0, V1)

    # print(cM)
    xy1 = linalg.solve(cM, cV)
    xy1_ = spla.bicg(cM, cV)[0]
    print(xy1_)
    plt.plot(np.real(z1), np.imag(z1))
    plt.plot(xy1_[0::2], xy1_[1::2])
    plt.show()
    """
if __name__ == '__main__':
    main()

"""
def make_grid_seko(z1, z2, z3, z4):
    def offset_surface(z):
        size = z.shape[0]

        delta = np.zeros(size, dtype=complex)
        delta[0] = z[1] - z[size - 1]
        for i in range(1, size - 1):
            delta[i] = z[i + 1] - z[i - 1]
        delta[size - 1] = z[0] - z[size - 2]

        normal = -1j * delta / np.abs(delta)
        incremental = 1.0*np.min(np.abs(delta))
        return z - normal * incremental

    def set_boundary(j):
        grid_x[0, j] = grid_x[xi_max, j]
        grid_x[1, j] = grid_x[xi_max+1, j]
        grid_x[xi_max+2, j] = grid_x[2, j]
        grid_x[xi_max+3, j] = grid_x[3, j]

        grid_y[0, j] = grid_y[xi_max, j]
        grid_y[1, j] = grid_y[xi_max+1, j]
        grid_y[xi_max+2, j] = grid_y[2, j]
        grid_y[xi_max+3, j] = grid_y[3, j]

    def deduplication(z, eps=0.0001):
        flag = 1
        while flag == 1:
            flag = 0
            if np.abs(z[0] - z[z.shape[0] - 1]) <= eps:
                z = z[:z.shape[0] - 1]
                flag = 1
        return z

    z1 = deduplication(z1)
    z0 = offset_surface(z1)
    xi_max = z1.shape[0]  # xi方向の格子点数
    eta_max = z2.shape[0]  # eta方向の格子点数
    grid_x = np.zeros((xi_max+4, eta_max+1))  # x座標格納   # xi方向は左右に2ずつ境界用，etaは後方に1つ境界用を用意
    grid_y = np.zeros((xi_max+4, eta_max+1))  # y座標格納   # 0(xi_max), 1(xi_max+1), 2(start), ... xi_max+1(end), xi_max+2(2), xi_max+3(3)
    # 境界条件適用
    grid_x[2:xi_max+2, 0] = np.real(z0)
    grid_y[2:xi_max+2, 0] = np.imag(z0)
    grid_x[2:xi_max+2, 1] = np.real(z1)  # 基準
    grid_y[2:xi_max+2, 1] = np.imag(z1)  # 底辺

    set_boundary(0)
    set_boundary(1)

    grid_vol = np.ones((xi_max + 4, eta_max + 1))
    for j in range(eta_max+1):
        grid_vol[:, j] = (j + 1) / eta_max
    grid_phi = np.zeros((xi_max+4, eta_max+1))

    # 以降係数は無視し，足し合わせる際に帳尻を合わせる
    x_xi = lambda i, j: (grid_x[i + 1, j - 1] - grid_x[i - 1, j - 1])   # xのξ微分(の2倍)
    x_eta = lambda i, j: (grid_x[i, j - 1] - grid_x[i, j - 2])  # xのη微分(の2倍)
    y_xi = lambda i, j: (grid_y[i + 1, j - 1] - grid_y[i - 1, j - 1])   # yのξ微分(の2倍)
    y_eta = lambda i, j:(grid_y[i, j - 1] - grid_y[i, j - 2])   # yのη微分(の2倍)

    Aij = lambda i, j: 0.25 * np.array([[x_eta(i, j), y_eta(i, j)], [y_eta(i, j), -x_eta(i, j)]])
    invAij = lambda i, j: np.linalg.inv(Aij(i, j))

    Bij = lambda i, j: 0.5 * np.array([[x_xi(i, j), y_xi(i, j)], [-y_xi(i, j), x_xi(i, j)]])
    invABij = lambda i, j: np.dot(invAij(i, j), Bij(i, j))

    invABij11 = lambda i, j: invABij(i, j)[0, 0]
    invABij12 = lambda i, j: invABij(i, j)[0, 1]
    invABij21 = lambda i, j: invABij(i, j)[1, 0]
    invABij22 = lambda i, j: invABij(i, j)[1, 1]

    const = lambda i, j: np.array([(-grid_phi[i, j] * grid_vol[i, j]**2 - grid_phi[i, j - 1] * grid_vol[i, j-1]**2), grid_vol[i, j] + grid_vol[i, j - 1]])
    const_x_ij = lambda i, j: np.dot(invAij(i, j), const(i, j))[0]
    const_y_ij = lambda i, j: np.dot(invAij(i, j), const(i, j))[1]

    rhs_x = lambda i, j: np.dot(invABij(i, j), np.array([grid_x[i, j - 1], grid_y[i, j - 1]]))[0]
    rhs_y = lambda i, j: np.dot(invABij(i, j), np.array([grid_x[i, j - 1], grid_y[i, j - 1]]))[1]

    fourth_eps_x = lambda i, j: grid_x[i+2,j-1] - 4.0 * grid_x[i + 1, j - 1] + 6.0 * grid_x[i,j-1] - 4.0 * grid_x[i-1,j-1] + grid_x[i-2,j-1]
    fourth_eps_y = lambda i, j: grid_y[i + 2, j - 1] - 4.0 * grid_y[i + 1, j - 1] + 6.0 * grid_y[i, j - 1] - 4.0 * grid_y[i - 1, j - 1] + grid_y[i - 2, j - 1]

    beta_x_ij = lambda i, j: const_x_ij(i, j) + rhs_x(i, j) + fourth_eps_x(i, j)
    beta_y_ij = lambda i, j: const_y_ij(i, j) + rhs_y(i, j) + fourth_eps_y(i, j)

    point_number = 2*xi_max

    # xについての式 + yについての式

    for j in range(2, eta_max+1):
        matrix = lil_matrix((point_number, point_number))   # 係数行列matrixの初期化
        rhs = np.zeros(point_number)
        for k in range(2*xi_max):
            if k < xi_max:
                i = k + 2   # 境界を含めた格子の番号
            else:
                i = k + 2 - xi_max

            # main diagonal element
            if k < xi_max:
                matrix[k, k] = invABij11(i, j)
                matrix[k, k + xi_max] = invABij12(i, j)
            else:
                matrix[k, k - xi_max] = invABij21(i, j)
                matrix[k, k] = invABij22(i, j)

            # left diagonal element
            if k == 0:
                matrix[k, k + xi_max - 1] = -1
                matrix[k, k + 2*xi_max - 1] = -1
            elif k < xi_max + 1:
                matrix[k, k-1] = -1
                matrix[k, k-1 + xi_max] = -1
            else:
                matrix[k, k-1] = -1
                matrix[k, k-1 - xi_max] = -1

            # right diagonal element
            if k < xi_max - 1:
                matrix[k, k + 1] = 1
                matrix[k, k+1+xi_max] = 1
            elif k < 2*xi_max-1:
                matrix[k, k+1] = 1
                matrix[k, k+1-xi_max] = 1
            else:
                matrix[k, k+1-xi_max] = 1
                matrix[k, k+1-2*xi_max] = 1

            if k < xi_max:
                rhs[k] = beta_x_ij(i, j)
            else:
                rhs[k] = beta_y_ij(i, j)

        matrix = matrix.tocsr()
        delta_xy = spsolve(matrix, rhs)

        grid_x[2:xi_max + 2, j] = delta_xy[:xi_max]
        grid_y[2:xi_max + 2, j] = delta_xy[xi_max:]
        set_boundary(j)
        plt.plot(grid_x[2:xi_max + 2, j], grid_y[2:xi_max + 2, j], "x")
        plt.show()

    for j in range(eta_max):
        plt.plot(grid_x[2:xi_max+2, j+1], grid_y[2:xi_max+2, j+1], "x")
    plt.show()
    exit()
# return grid_x, grid_y


# a, b, cからなる三重対角行列(n×n)および，n次元定数ベクトルdの連立方程式の解xを返す
# aは2行目からb行目まで，cは1行目からn-1行まで
def tridiagonal_matrix_algorithm(a, b, c, d, n):
    c_prime = np.zeros(n)
    d_prime = np.zeros(n)
    x = np.zeros(n)
    c_prime[0] = c[0] / b[0]
    d_prime[0] = d[0] / b[0]

    for i in range(1, n - 1):
        c_prime[i] = c[i] / (b[i] - a[i] * c_prime[i - 1])
        d_prime[i] = (d[i] - a[i] * d_prime[i - 1]) / (b[i] - a[i] * c_prime[i - 1])

    d_prime[n-1] = (d[n-1] - a[n-1] * d_prime[n-2]) / (b[n-1] - a[n-1] * c_prime[n-2])

    x[n-1] = d_prime[n-1]
    for i in range(n-2, -1, -1):
        x[i] = d_prime[i] - c_prime[i] * x[i + 1]

    return x

def check_TDMA():
    N = 5
    A = np.zeros((N, N))
    A[0, 0] = 3
    A[0, 1] = 4
    for i in range(1, N-1):
        A[i, i-1] = 2+i
        A[i, i] = 3
        A[i, i+1] = 4
    A[N-1, N-2] = 2+N-1
    A[N-1, N-1] = 3
    print(A)

    b = np.arange(5)
    print(linalg.det(A))
    print(b)
    print(linalg.solve(A, b))
    left = np.arange(5) + 3 - 1
    diag = np.ones(5) * 3
    right = np.ones(5) * 4

    print(tridiagonal_matrix_algorithm(left, diag, right, b, 5))
    exit()
"""
"""
def make_grid_seko(z1, z2, z3, z4):
    xi_max = z1.shape[0]  # xi方向の格子点数
    eta_max = z2.shape[0]  # eta方向の格子点数
    center_x = 0.25 * (np.average(np.real(z1)) + np.average(np.real(z2)) + np.average(np.real(z3)) + np.average(np.real(z4)))
    center_y = 0.25 * (np.average(np.imag(z1)) + np.average(np.imag(z2)) + np.average(np.imag(z3)) + np.average(np.imag(z4)))
    grid_x = np.zeros((xi_max, eta_max))  # x座標格納
    grid_y = np.zeros((xi_max, eta_max))  # y座標格納
    for i in range(eta_max):
        grid_x[i, :] = np.linspace(np.real(z1[i]), np.real(z3[eta_max-1-i]), eta_max)
        grid_y[i, :] = np.linspace(np.imag(z1[i]), np.imag(z3[eta_max-1-i]), eta_max)
    for i in range(xi_max):
        plt.plot(grid_x[i, :], grid_y[i, :])
        plt.plot(grid_x[:, i], grid_y[:, i])

    plt.show()
    # 境界条件適用
    grid_x[0, :] = np.real(z1)  # 底辺
    grid_x[:, 0] = np.real(z2)  # 左辺
    grid_x[xi_max - 1, :] = np.real(z3)  # 上辺
    grid_x[:, eta_max - 1] = np.real(z4)

    grid_y[0, :] = np.imag(z1)  # 底辺
    grid_y[:, 0] = np.imag(z2)[::-1]  # 左辺
    grid_y[xi_max - 1, :] = np.imag(z3) # 上辺
    grid_y[:, eta_max - 1] = np.imag(z4)    # 右辺

    # 以降係数は無視し，足し合わせる際に帳尻を合わせる
    x_xi = lambda i, j: (grid_x[i + 1, j] - grid_x[i - 1, j])   # xのξ微分(の2倍)
    x_eta = lambda i, j: (grid_x[i, j + 1] - grid_x[i, j - 1])  # xのη微分(の2倍)
    y_xi = lambda i, j: (grid_y[i + 1, j] - grid_y[i - 1, j])   # yのξ微分(の2倍)
    y_eta = lambda i, j:(grid_y[i, j + 1] - grid_y[i, j - 1])   # yのη微分(の2倍)
    
    Aij = lambda i, j: (x_eta(i, j) ** 2 + y_eta(i, j) ** 2)    # ξ2階微分の係数(の4倍)
    Bij = lambda i, j: (x_xi(i, j) * x_eta(i, j) + y_xi(i, j) * y_eta(i, j))    # ξη交差微分の係数(の4倍)
    Cij = lambda i, j: (x_xi(i, j) ** 2 + y_xi(i, j) ** 2)    # η2階微分の係数(の4倍)
    
    x_xixi = lambda i, j: grid_x[i + 1, j] - 2.0 * grid_x[i, j] + grid_x[i - 1, j]  # xのξ2階微分
    y_xixi = lambda i, j: grid_y[i + 1, j] - 2.0 * grid_y[i, j] + grid_y[i - 1, j]  # yのξ2階微分
    
    x_etaeta = lambda i, j: grid_x[i, j + 1] - 2.0 * grid_x[i, j] + grid_x[i, j - 1]    # xのη2階微分
    y_etaeta = lambda i, j: grid_y[i, j + 1] - 2.0 * grid_y[i, j] + grid_y[i, j - 1]    # yのη2階微分
    
    x_xieta = lambda i, j: (grid_x[i + 1, j + 1] - grid_x[i + 1, j - 1] - grid_x[i - 1, j + 1] + grid_x[i - 1, j - 1])  # xのξη交差微分(の4倍)
    y_xieta = lambda i, j: (grid_y[i + 1, j + 1] - grid_y[i + 1, j - 1] - grid_y[i - 1, j + 1] + grid_y[i - 1, j - 1])  # yのξη交差微分(の4倍)

    
    delta_t = 0.0001  # delta-formの時間発展用
    point_number = (xi_max - 2) * (eta_max - 2) # 未知数の総数
    Nj = eta_max - 2    # 係数行列の列方向ブロックサイズ
    
    # [I,I]からdeltaだけずれた位置の成分が何個目のブロック行列に属するか返す関数
    block_id = lambda delta: floor((I + delta) / Nj)
    # xについての式 + yについての式
    for iter in range(1000):
        # matrix & rhsの準備
        # rhs = np.zeros(2 * point_number)    # rhsベクトルの初期化
        sol = np.zeros(2 * point_number)    # 解ベクトルの初期化
        # matrix = lil_matrix((2 * point_number, 2 * point_number))   # 係数行列matrixの初期化
        dij = 0
        for I in range(point_number):
            block = block_id(0) # 現在のブロック
            i = I - block * Nj + 1  # 未知数の0 = 1番目の格子点(0番目の格子点は更新する必要がないため放置) # matrixの0番はgrid_xyの1番に相当
            j = block + 1  # aij対策で+1
            
            aij = Aij(i, j) # I行内では常に同じ添え字ijを用いるため最初に計算しておく
            bij = Bij(i, j)
            cij = Cij(i, j)
            dij = max(max(aij, bij), max(cij, dij))

            matrix[I, I] = 1.0 - delta_t * 2.0 * (aij + cij)    # xの係数
            matrix[I + point_number, I + point_number] = 1.0 - delta_t * 2.0 * (aij + cij)  # yの係数
            
            # AΔt
            if (I > 0) and (block_id(-1) == block):  # 対角成分と同一ブロック内にないときは0
                matrix[I, I - 1] = delta_t * aij
                matrix[I + point_number, I + point_number - 1] = delta_t * aij
            if (I < point_number - 1) and (block_id(1) == block):
                matrix[I, I + 1] = delta_t * aij
                matrix[I + point_number, I + point_number + 1] = delta_t * aij
            
            # CΔt
            if I > Nj - 1:
                matrix[I, I - Nj] = delta_t * cij
                matrix[I + point_number, I + point_number - Nj] = delta_t * cij
            if I < point_number - Nj:
                matrix[I, I + Nj] = delta_t * cij
                matrix[I + point_number, I + point_number + Nj] = delta_t * cij
            
            # -0.5*bij
            if ((I > (Nj - 1)) and (block_id(-(Nj - 1)) == block - 1)):
                matrix[I, I - (Nj - 1)] = - delta_t * 0.5 * bij
                matrix[I + point_number, I + point_number - (Nj - 1)] = - delta_t * 0.5 * bij
            if ((I < point_number - (Nj - 1)) and (block_id(Nj - 1) == block + 1)):
                matrix[I, I + (Nj - 1)] = - delta_t * 0.5 * bij
                matrix[I + point_number, I + point_number + (Nj - 1)] = - delta_t * 0.5 * bij
            
            # +0.5*bij
            if ((I > (Nj + 1) - 1 and (block_id(-(Nj + 1)) == block - 1))):
                matrix[I, I - (Nj + 1)] = delta_t * 0.5 * bij
                matrix[I + point_number, I + point_number - (Nj + 1)] = delta_t * 0.5 * bij
            if ((I < point_number - (Nj + 1) - 1) and (block_id(Nj + 1) == block + 1)):
                matrix[I, I + (Nj + 1)] = delta_t * 0.5 * bij
                matrix[I + point_number, I + point_number + (Nj + 1)] = delta_t * 0.5 * bij
            # rhs[I] = - delta_t * (aij * x_xixi(i, j) - 0.5 * bij * x_xieta(i, j) + cij * x_etaeta(i, j))
            # rhs[I + point_number] = -delta_t * (aij * y_xixi(i, j) - 0.5 * bij * y_xieta(i, j) + cij * y_etaeta(i, j))
            sol[I] = (aij * x_xixi(i, j) - 0.5 * bij * x_xieta(i, j) + cij * x_etaeta(i, j))
            sol[I + point_number] = (aij * y_xixi(i, j) - 0.5 * bij * y_xieta(i, j) + cij * y_etaeta(i, j))
        
        # delta_xy = bicg(matrix, rhs)[0]
        # matrix = matrix.tocsr()
        # delta_xy = spsolve(matrix, rhs)

        delta_t = 1.0 / (3.0 * dij)
        # grid_x[1:xi_max - 1, 1:eta_max - 1] += delta_xy[:point_number].reshape(xi_max - 2, -1).T
        # grid_y[1:xi_max - 1, 1:eta_max - 1] += delta_xy[point_number:].reshape(xi_max - 2, -1).T
        grid_x[1:xi_max - 1, 1:eta_max - 1] = delta_t * sol[:point_number].reshape(xi_max - 2, -1).T + grid_x[1:xi_max - 1, 1:eta_max - 1]
        grid_y[1:xi_max - 1, 1:eta_max - 1] = delta_t * sol[point_number:].reshape(xi_max - 2, -1).T + grid_y[1:xi_max - 1, 1:eta_max - 1]
        # maximum = max(np.max(np.abs(grid_x)), np.max(np.abs(grid_y)))
        # print(maximum)
        if iter % 50 == 0:
            for i in range(xi_max):
                plt.plot(grid_x[i, :], grid_y[i, :])
                plt.plot(grid_x[:, i], grid_y[:, i])

            plt.show()


# return grid_x, grid_y
"""
"""
def make_grid_seko(z1, z2, z3, z4):
    xi_max = z1.shape[0]  # xi方向の格子点数
    eta_max = z2.shape[0]  # eta方向の格子点数
    
    grid_x = np.zeros((xi_max, eta_max))  # x座標格納
    grid_y = np.zeros((xi_max, eta_max))  # y座標格納
    # 境界条件適用
    grid_x[0, :] = np.real(z1)  # 底辺
    grid_x[:, 0] = np.real(z2)  # 左辺
    grid_x[xi_max - 1, :] = np.real(z3)  # 上辺
    grid_x[:, eta_max - 1] = np.real(z4)

    grid_y[0, :] = np.imag(z1)  # 底辺
    grid_y[:, 0] = np.imag(z2)[::-1]  # 左辺
    grid_y[xi_max - 1, :] = np.imag(z3) # 上辺
    grid_y[:, eta_max - 1] = np.imag(z4)    # 右辺

    # 以降係数は無視し，足し合わせる際に帳尻を合わせる
    x_xi = lambda i, j: (grid_x[i + 1, j] - grid_x[i - 1, j])   # xのξ微分
    x_eta = lambda i, j: (grid_x[i, j + 1] - grid_x[i, j - 1])  # xのη微分
    y_xi = lambda i, j: (grid_y[i + 1, j] - grid_y[i - 1, j])   # yのξ微分
    y_eta = lambda i, j:(grid_y[i, j + 1] - grid_y[i, j - 1])   # yのη微分
    
    Aij = lambda i, j: (x_eta(i, j) ** 2 + y_eta(i, j) ** 2)    # ξ2階微分の係数
    Bij = lambda i, j: (x_xi(i, j) * x_eta(i, j) + y_xi(i, j) * y_eta(i, j))    # ξη交差微分の係数
    Cij = lambda i, j: (x_xi(i, j) ** 2 + y_xi(i, j) ** 2)    # η2階微分の係数
    
    x_xixi = lambda i, j: grid_x[i + 1, j] - 2.0 * grid_x[i, j] + grid_x[i - 1, j]  # xのξ2階微分
    y_xixi = lambda i, j: grid_y[i + 1, j] - 2.0 * grid_y[i, j] + grid_y[i - 1, j]  # yのξ2階微分
    
    x_etaeta = lambda i, j: grid_x[i, j + 1] - 2.0 * grid_x[i, j] + grid_x[i, j - 1]    # xのη2階微分
    y_etaeta = lambda i, j: grid_y[i, j + 1] - 2.0 * grid_y[i, j] + grid_y[i, j - 1]    # yのη2階微分
    
    x_xieta = lambda i, j: (grid_x[i + 1, j + 1] - grid_x[i + 1, j - 1] - grid_x[i - 1, j + 1] + grid_x[i - 1, j - 1])  # xのξη交差微分
    y_xieta = lambda i, j: (grid_y[i + 1, j + 1] - grid_y[i + 1, j - 1] - grid_y[i - 1, j + 1] + grid_y[i - 1, j - 1])  # yのξη交差微分

    
    delta_t = 0.1  # delta-formの時間発展用
    point_number = (xi_max - 2) * (eta_max - 2) # 未知数の総数
    Nj = eta_max - 2    # 係数行列の列方向ブロックサイズ
    
    # [I,I]からdeltaだけずれた位置の成分が何個目のブロック行列に属するか返す関数
    block_id = lambda delta: floor((I + delta) / Nj)
    # xについての式 + yについての式
    for iter in range(1000):
        # matrix & rhsの準備
        rhs = np.zeros(2 * point_number)    # rhsベクトルの初期化
        matrix = lil_matrix((2 * point_number, 2 * point_number))   # 係数行列matrixの初期化
        for I in range(point_number):
            block = block_id(0) # 現在のブロック
            i = I - block * Nj + 1  # 未知数の0 = 1番目の格子点(0番目の格子点は更新する必要がないため放置) # matrixの0番はgrid_xyの1番に相当
            j = block + 1  # aij対策で+1
            
            aij = Aij(i, j) # I行内では常に同じ添え字ijを用いるため最初に計算しておく
            bij = Bij(i, j)
            cij = Cij(i, j)
            
            matrix[I, I] = 1.0 - delta_t * 2.0 * (aij + cij)    # xの係数
            matrix[I + point_number, I + point_number] = 1.0 - delta_t * 2.0 * (aij + cij)  # yの係数
            
            # AΔt
            if (I > 0) and (block_id(-1) == block):  # 対角成分と同一ブロック内にないときは0
                matrix[I, I - 1] = delta_t * aij
                matrix[I + point_number, I + point_number - 1] = delta_t * aij
            if (I < point_number - 1) and (block_id(1) == block):
                matrix[I, I + 1] = delta_t * aij
                matrix[I + point_number, I + point_number + 1] = delta_t * aij
            
            # CΔt
            if I > Nj - 1:
                matrix[I, I - Nj] = delta_t * cij
                matrix[I + point_number, I + point_number - Nj] = delta_t * cij
            if I < point_number - Nj:
                matrix[I, I + Nj] = delta_t * cij
                matrix[I + point_number, I + point_number + Nj] = delta_t * cij
            
            # -0.5*bij
            if ((I > (Nj - 1)) and (block_id(-(Nj - 1)) == block - 1)):
                matrix[I, I - (Nj - 1)] = - delta_t * 0.5 * bij
                matrix[I + point_number, I + point_number - (Nj - 1)] = - delta_t * 0.5 * bij
            if ((I < point_number - (Nj - 1)) and (block_id(Nj - 1) == block + 1)):
                matrix[I, I + (Nj - 1)] = - delta_t * 0.5 * bij
                matrix[I + point_number, I + point_number + (Nj - 1)] = - delta_t * 0.5 * bij
            
            # +0.5*bij
            if ((I > (Nj + 1) - 1 and (block_id(-(Nj + 1)) == block - 1))):
                matrix[I, I - (Nj + 1)] = delta_t * 0.5 * bij
                matrix[I + point_number, I + point_number - (Nj + 1)] = delta_t * 0.5 * bij
            if ((I < point_number - (Nj + 1) - 1) and (block_id(Nj + 1) == block + 1)):
                matrix[I, I + (Nj + 1)] = delta_t * 0.5 * bij
                matrix[I + point_number, I + point_number + (Nj + 1)] = delta_t * 0.5 * bij

            rhs[I] = - delta_t * (aij * x_xixi(i, j) - 0.5 * bij * x_xieta(i, j) + cij * x_etaeta(i, j))
            rhs[I + point_number] = -delta_t * (aij * y_xixi(i, j) - 0.5 * bij * y_xieta(i, j) + cij * y_etaeta(i, j))
        
        delta_xy = bicg(matrix, rhs)[0]
        
        grid_x[1:xi_max - 1, 1:eta_max - 1] += delta_xy[:point_number].reshape(xi_max - 2, -1).T
        grid_y[1:xi_max - 1, 1:eta_max - 1] += delta_xy[point_number:].reshape(xi_max - 2, -1).T
        maximum = max(np.max(np.abs(grid_x)), np.max(np.abs(grid_y)))
        print(maximum)
        if maximum < 8:
            for i in range(xi_max):
                plt.plot(grid_x[i, :], grid_y[i, :])
            plt.show()
            
            for j in range(eta_max):
                plt.plot(grid_x[:, j], grid_y[:, j])
            plt.show()
"""

"""
def make_grid_seko(z1, z2, z3):
    # 極端に近い点を除去(内側を優先的に除去)
    def delete_near_point(z, eps=0.0001):
        flag = 1
        while flag == 1:
            flag = 0
            len = np.abs(z[1:] - z[:z.shape[0]-1])
            num = np.argmin(len)
            if len[num] < eps:
                z = np.hstack([z[:num], z[num+1:]])
                flag = 1
        return z
    
    # 終端の重複している座標点を除去
    def deduplication(z, eps=0.0001):
        z = delete_near_point(z)
        flag = 1
        while flag == 1:
            flag = 0
            if np.abs(z[0] - z[z.shape[0] - 1]) <= eps:
                z = z[:z.shape[0] - 1]
                flag = 1
        return z
    
    # 終端に重複する座標点を追加
    def add_duplicates(z, eps=0.0001):
        if np.abs(z[0] - z[z.shape[0] - 1]) > eps:
            z = np.hstack([z, z[0]])
        return z
    
    # 中心からの角度基準で座標点を並べ替える
    def sort_by_angle(z):
        center = np.average(np.real(z)) + 1j * np.average(np.imag(z))
        return z[np.argsort(np.angle(z - center))]
    
    def sort_for_cross_delete(z0, z1):
        def find_intersection_line_by_line(p1, p2, p3, p4):
            def det123(z1, z2, z3):
                # a = np.array([[1, 1, 1], [np.real(z1), np.real(z2), np.real(z3)], [np.imag(z1), np.imag(z2), np.imag(z3)]])
                return np.linalg.det(np.array(
                    [[1, 1, 1], [np.real(z1), np.real(z2), np.real(z3)], [np.imag(z1), np.imag(z2), np.imag(z3)]]))
            
            if det123(p1, p2, p3) * det123(p1, p2, p4) < 0:
                if det123(p3, p4, p1) * det123(p3, p4, p2) < 0:
                    return True
            
            return False
        
        def swap_a_b(a, b):
            return b, a
        
        def half_length(dz, z):
            return 0.5 * (dz + z)
        
        size = z0.shape[0]
        flag = 1
        while flag == 1:
            flag = 0
            for i in range(size-1):
                if find_intersection_line_by_line(z0[i], z0[i+1], z1[i], z1[i+1]):
                    # z1[i], z1[i + 1] = swap_a_b(z1[i], z1[i+1])
                    z1[i] = half_length(z1[i], z0[i])
                    z1[i+1] = half_length(z1[i+1], z0[i+1])
                    flag = 1
            if find_intersection_line_by_line(z0[size-1], z0[0], z1[size-1], z1[0]):
                # z1[size-1], z1[0] = swap_a_b(z1[size-1], z1[0])
                z1[size-1] = half_length(z1[size-1], z0[0])
                z1[0] = half_length(z1[0], z0[size-1])
                flag = 1
                
        return z1
        
    # 物体表面を押し出す
    def offset_surface(z):
        def get_angle(z2, z1, z0):
            # if (np.imag(z2 - z1) >= 0) and (np.imag(z1 - z0)):
            az21 = np.angle(z2 - z1)
            az01 = np.angle(z0 - z1)
            print(az21, az01)
            #if az21 < 0:
            #    return 0.5 * (az21 + az01) + np.pi
            return 0.5 * (az21 + az01)

        size = z.shape[0]
        
        delta = np.zeros(size, dtype = complex)
        delta[0] = z[1] - z[size -1]
        for i in range(1, size-1):
            delta[i] = z[i + 1] - z[i - 1]
        delta[size - 1] = z[0] - z[size - 2]

        normal = -1j * delta / np.abs(delta)
        incremental = np.min(np.abs(delta))
        dz = z + normal * incremental
        center = np.average(np.real(z)) + 1j * np.average(np.imag(z))
        # np.argsort(dz - center)
        dz = sort_for_cross_delete(z, dz)
        return z + normal * incremental, incremental
    
    z1 = deduplication(z1)
    # z1 = sort_by_angle(z1)
    
    size = z1.shape[0]
    z = np.zeros((size, size), dtype = complex)
    z[:, 0] = z1
    distance = 0
    plt.plot(np.real(z[:, 0]), np.imag(z[:, 0]))
    for j in range(1, size):
        z[:, j], incremental = offset_surface(z[:, j - 1])
        distance += incremental
        # plt.plot(np.real(z[:, j]), np.imag(z[:, j]))
        
    # for i in range(size):
        # plt.plot(np.real(z[i, :]), np.imag(z[i, :]))
    
    
    print(distance)
    # plt.show()

    for i in range(int(size / 7)):
        plt.plot(np.real(z[i, :]), np.imag(z[i, :]))
        plt.plot(np.real(z[:, i]), np.imag(z[:, i]))
    xbot = 0.8
    xtop = 1.0
    ybot = 0.3
    ytop = 0.5
    plt.xlim(xbot, xtop)
    plt.ylim(ybot, ytop)
    plt.show()
    exit()
"""
"""
    xi_max = z1.shape[0]    # xi方向の格子点数
    eta_max = z2.shape[0]   # eta方向の格子点数

    grid_x = np.zeros((xi_max, eta_max))    # x座標格納
    grid_y = np.zeros((xi_max, eta_max))    # y座標格納

    center = np.average(np.real(z1))
    eps = 0.01
    min_rad = np.max(np.abs(z1 + center)) + eps
    max_rad = np.min(np.abs(z3 + center)) - eps
    radius = np.linspace(min_rad, max_rad, xi_max)

    for i in range(1, xi_max-1):
        circle = center + radius[i-1] * np.exp(1j*np.linspace(0, 2.0*np.pi, eta_max))
        grid_x[i, :] = np.real(circle)
        grid_y[i, :] = np.imag(circle)
    z3 = z3[::-1]

    # 境界条件適用
    grid_x[:, 0] = np.real(z2)  # 左辺
    grid_x[0, :] = np.real(z1)  # 底辺
    grid_x[xi_max-1, :] = np.real(z3)    # 上辺
    grid_x[:, eta_max - 1] = np.real(z2)

    grid_y[0, :] = np.imag(z1)  # 底辺
    grid_y[:, 0] = np.imag(z2) + eps    # 左辺
    grid_y[xi_max - 1, :] = np.imag(z3)
    grid_y[:, eta_max - 1] = np.imag(z2) - eps


    for i in range(xi_max):
        plt.plot(grid_x[i, :], grid_y[i, :])
    plt.show()
    for j in range(eta_max):
        plt.plot(grid_x[:, j], grid_y[:, j])
    plt.show()

    diff_x_xi = lambda i, j: 0.5 * (grid_x[i+1, j] - grid_x[i-1, j])
    diff_y_xi = lambda i, j: 0.5 * (grid_y[i+1, j] - grid_y[i-1, j])
    diff_x_eta = lambda i, j: 0.5 * (grid_x[i, j+1] - grid_x[i, j-1])
    diff_y_eta = lambda i, j: 0.5 * (grid_y[i, j+1] - grid_y[i, j-1])

    Aij = lambda i, j: (diff_x_eta(i, j)**2 + diff_y_eta(i, j)**2)
    Bij = lambda i, j: (diff_x_xi(i, j) * diff_x_eta(i, j) + diff_y_xi(i, j) * diff_y_eta(i, j))
    Cij = lambda i, j: (diff_x_xi(i, j)**2 + diff_y_xi(i, j)**2)

    diff_x_xixi = lambda i, j: grid_x[i+1, j] - 2.0 * grid_x[i, j] + grid_x[i-1, j]
    diff_y_xixi = lambda i, j: grid_y[i+1, j] - 2.0 * grid_y[i, j] + grid_y[i-1, j]

    diff_x_etaeta = lambda i, j: grid_x[i, j+1] - 2.0 * grid_x[i, j] + grid_x[i, j-1]
    diff_y_etaeta = lambda i, j: grid_y[i, j+1] - 2.0 * grid_y[i, j] + grid_y[i, j-1]

    diff_x_xieta = lambda i, j: grid_x[i+1, j+1] - grid_x[i+1, j-1] - grid_x[i-1, j+1] + grid_x[i-1, j-1]
    diff_y_xieta = lambda i, j: grid_y[i+1, j+1] - grid_y[i+1, j-1] - grid_y[i-1, j+1] + grid_y[i-1, j-1]

    delta_t = 0.01
    theta = 0.5
    delta_t *= theta
    point_number = (xi_max - 2) * (eta_max - 2)
    Ni = xi_max - 2
    Nj = eta_max - 2

    # [I,I]からdeltaだけずれた位置の成分が何列目のブロック行列に属するか返す
    block_id = lambda delta: floor((I + delta) / Nj)

    for iter in range(1000):
        # matrix & rhsの準備
        rhs = np.zeros(2 * point_number)
        matrix = lil_matrix((2 * point_number, 2 * point_number))
        for I in range(point_number):
            block = block_id(0)
            i = I - block * Nj + 1    # aij対策で+1  # matrixの0番はgrid_xyの1番に相当
            j = block + 1 # aij対策で+1

            aij = Aij(i, j)
            bij = Bij(i,j)
            cij = Cij(i, j)

            matrix[I, I] = 1.0 - delta_t * 2.0 * (aij + cij)
            matrix[I + point_number, I + point_number] = 1.0 - delta_t * 2.0 * (aij + cij)
            # x-direction
            if (I > 0) and (block_id(-1) == block): # 対角成分と同一ブロック内にないときは0
                matrix[I, I-1] = delta_t * aij
                matrix[I + point_number, I + point_number - 1] = delta_t * aij
            if (I < point_number-1) and (block_id(1) == block):
                matrix[I, I+1] = delta_t * aij
                matrix[I + point_number, I + point_number + 1] = delta_t * aij

            if I > Nj - 1:
                matrix[I, I-Nj] = delta_t * cij
                matrix[I + point_number, I + point_number - Nj] = delta_t * cij
            if I < point_number - Nj:
                matrix[I, I + Nj] = delta_t * cij
                matrix[I + point_number, I + point_number + Nj] = delta_t * cij

            if ((I > (Nj - 1)) and (block_id(-(Nj - 1)) == block-1)):
                matrix[I, I-(Nj-1)] = delta_t * 2.0 * bij
                matrix[I + point_number, I + point_number - (Nj - 1)] = delta_t * 2.0 * bij
            if ((I < point_number - (Nj - 1)) and (block_id(Nj - 1) == block + 1)):
                matrix[I, I+(Nj-1)] = delta_t * 2.0 * bij
                matrix[I + point_number, I + point_number + (Nj - 1)] = delta_t * 2.0 * bij


            if ((I > (Nj + 1) - 1 and (block_id(-(Nj+1)) == block - 1))):
                matrix[I, I-(Nj+1)] = - delta_t * 2.0 * bij
                matrix[I + point_number, I + point_number - (Nj + 1)] = -delta_t * 2.0 * bij
            if ((I < point_number - (Nj + 1) - 1) and (block_id(Nj + 1) == block + 1)):
                matrix[I, I+(Nj+1)] = -delta_t * 2.0 * bij
                matrix[I + point_number, I + point_number + (Nj + 1)] = - delta_t * 2.0 * bij
            if I==10:
                print(aij)
            rhs[I] = -delta_t * (aij * diff_x_xixi(i, j) - 2.0 * bij * diff_x_xieta(i, j) + cij * diff_x_etaeta(i, j))
            rhs[I + point_number] = -delta_t * (aij * diff_y_xixi(i, j) - 2.0 * bij * diff_y_xieta(i, j) + cij * diff_y_etaeta(i, j))

        rhs /= theta
        delta_xy = bicg(matrix, rhs)[0]

        grid_x[1:xi_max-1, 1:eta_max-1] += delta_xy[:point_number].reshape(xi_max-2, -1)
        grid_y[1:xi_max-1, 1:eta_max-1] += delta_xy[point_number:].reshape(xi_max-2, -1)

        for i in range(xi_max):
            plt.plot(grid_x[i, :], grid_y[i, :])
        plt.show()

        for j in range(eta_max):
            plt.plot(grid_x[:, j], grid_y[:, j])
        plt.show()

    # return grid_x, grid_y
"""
"""
def make_grid(z1, z2, z3):
    xi_max = z1.shape[0]    # xi方向の格子点数
    eta_max = z2.shape[0]   # eta方向の格子点数

    grid_x = np.zeros((xi_max, eta_max))    # x座標格納
    grid_y = np.zeros((xi_max, eta_max))    # y座標格納

    center = np.average(np.real(z1))
    eps = 0.01
    min_rad = np.max(np.abs(z1 + center)) + eps
    max_rad = np.min(np.abs(z3 + center)) - eps
    radius = np.linspace(min_rad, max_rad, xi_max)

    for i in range(1, xi_max-1):
        circle = center + radius[i-1] * np.exp(1j*np.linspace(0, 2.0*np.pi, eta_max))
        grid_x[i, :] = np.real(circle)
        grid_y[i, :] = np.imag(circle)
    z3 = z3[::-1]

    # 境界条件適用
    grid_x[:, 0] = np.real(z2)  # 左辺
    grid_x[0, :] = np.real(z1)  # 底辺
    grid_x[xi_max-1, :] = np.real(z3)    # 上辺
    grid_x[:, eta_max - 1] = np.real(z2)

    grid_y[0, :] = np.imag(z1)  # 底辺
    grid_y[:, 0] = np.imag(z2) + eps    # 左辺
    grid_y[xi_max - 1, :] = np.imag(z3)
    grid_y[:, eta_max - 1] = np.imag(z2) - eps


    for i in range(xi_max):
        plt.plot(grid_x[i, :], grid_y[i, :])
    plt.show()
    for j in range(eta_max):
        plt.plot(grid_x[:, j], grid_y[:, j])
    plt.show()

    diff_x_xi = lambda i, j: 0.5 * (grid_x[i+1, j] - grid_x[i-1, j])
    diff_y_xi = lambda i, j: 0.5 * (grid_y[i+1, j] - grid_y[i-1, j])
    diff_x_eta = lambda i, j: 0.5 * (grid_x[i, j+1] - grid_x[i, j-1])
    diff_y_eta = lambda i, j: 0.5 * (grid_y[i, j+1] - grid_y[i, j-1])

    Aij = lambda i, j: (diff_x_eta(i, j)**2 + diff_y_eta(i, j)**2)
    Bij = lambda i, j: (diff_x_xi(i, j) * diff_x_eta(i, j) + diff_y_xi(i, j) * diff_y_eta(i, j))
    Cij = lambda i, j: (diff_x_xi(i, j)**2 + diff_y_xi(i, j)**2)

    diff_x_xixi = lambda i, j: grid_x[i+1, j] - 2.0 * grid_x[i, j] + grid_x[i-1, j]
    diff_y_xixi = lambda i, j: grid_y[i+1, j] - 2.0 * grid_y[i, j] + grid_y[i-1, j]

    diff_x_etaeta = lambda i, j: grid_x[i, j+1] - 2.0 * grid_x[i, j] + grid_x[i, j-1]
    diff_y_etaeta = lambda i, j: grid_y[i, j+1] - 2.0 * grid_y[i, j] + grid_y[i, j-1]

    diff_x_xieta = lambda i, j: grid_x[i+1, j+1] - grid_x[i+1, j-1] - grid_x[i-1, j+1] + grid_x[i-1, j-1]
    diff_y_xieta = lambda i, j: grid_y[i+1, j+1] - grid_y[i+1, j-1] - grid_y[i-1, j+1] + grid_y[i-1, j-1]

    delta_t = 0.01
    theta = 0.5
    delta_t *= theta
    point_number = (xi_max - 2) * (eta_max - 2)
    Ni = xi_max - 2
    Nj = eta_max - 2

    # [I,I]からdeltaだけずれた位置の成分が何列目のブロック行列に属するか返す
    block_id = lambda delta: floor((I + delta) / Nj)

    for iter in range(1000):
        # matrix & rhsの準備
        rhs = np.zeros(2 * point_number)
        matrix = lil_matrix((2 * point_number, 2 * point_number))
        for I in range(point_number):
            block = block_id(0)
            i = I - block * Nj + 1    # aij対策で+1  # matrixの0番はgrid_xyの1番に相当
            j = block + 1 # aij対策で+1

            aij = Aij(i, j)
            bij = Bij(i,j)
            cij = Cij(i, j)

            matrix[I, I] = 1.0 - delta_t * 2.0 * (aij + cij)
            matrix[I + point_number, I + point_number] = 1.0 - delta_t * 2.0 * (aij + cij)
            # x-direction
            if (I > 0) and (block_id(-1) == block): # 対角成分と同一ブロック内にないときは0
                matrix[I, I-1] = delta_t * aij
                matrix[I + point_number, I + point_number - 1] = delta_t * aij
            if (I < point_number-1) and (block_id(1) == block):
                matrix[I, I+1] = delta_t * aij
                matrix[I + point_number, I + point_number + 1] = delta_t * aij

            if I > Nj - 1:
                matrix[I, I-Nj] = delta_t * cij
                matrix[I + point_number, I + point_number - Nj] = delta_t * cij
            if I < point_number - Nj:
                matrix[I, I + Nj] = delta_t * cij
                matrix[I + point_number, I + point_number + Nj] = delta_t * cij

            if ((I > (Nj - 1)) and (block_id(-(Nj - 1)) == block-1)):
                matrix[I, I-(Nj-1)] = delta_t * 2.0 * bij
                matrix[I + point_number, I + point_number - (Nj - 1)] = delta_t * 2.0 * bij
            if ((I < point_number - (Nj - 1)) and (block_id(Nj - 1) == block + 1)):
                matrix[I, I+(Nj-1)] = delta_t * 2.0 * bij
                matrix[I + point_number, I + point_number + (Nj - 1)] = delta_t * 2.0 * bij


            if ((I > (Nj + 1) - 1 and (block_id(-(Nj+1)) == block - 1))):
                matrix[I, I-(Nj+1)] = - delta_t * 2.0 * bij
                matrix[I + point_number, I + point_number - (Nj + 1)] = -delta_t * 2.0 * bij
            if ((I < point_number - (Nj + 1) - 1) and (block_id(Nj + 1) == block + 1)):
                matrix[I, I+(Nj+1)] = -delta_t * 2.0 * bij
                matrix[I + point_number, I + point_number + (Nj + 1)] = - delta_t * 2.0 * bij
            if I==10:
                print(aij)
            rhs[I] = -delta_t * (aij * diff_x_xixi(i, j) - 2.0 * bij * diff_x_xieta(i, j) + cij * diff_x_etaeta(i, j))
            rhs[I + point_number] = -delta_t * (aij * diff_y_xixi(i, j) - 2.0 * bij * diff_y_xieta(i, j) + cij * diff_y_etaeta(i, j))

        rhs /= theta
        delta_xy = bicg(matrix, rhs)[0]

        grid_x[1:xi_max-1, 1:eta_max-1] += delta_xy[:point_number].reshape(xi_max-2, -1)
        grid_y[1:xi_max-1, 1:eta_max-1] += delta_xy[point_number:].reshape(xi_max-2, -1)

        for i in range(xi_max):
            plt.plot(grid_x[i, :], grid_y[i, :])
        plt.show()

        for j in range(eta_max):
            plt.plot(grid_x[:, j], grid_y[:, j])
        plt.show()
"""
"""
def make_grid(z1, z2, z3):
    xi_max = z1.shape[0]    # xi方向の格子点数
    eta_max = z2.shape[0]   # eta方向の格子点数

    grid_x = np.zeros((xi_max, eta_max))    # x座標格納
    grid_y = np.zeros((xi_max, eta_max))    # y座標格納
    # 境界条件適用
    grid_x[:, 0] = np.real(z1)  # 底辺
    grid_x[0, :] = np.real(z2)  # 左辺
    grid_x[:, eta_max - 1] = np.real(z3)    # 上辺
    grid_x[xi_max - 1, :] = np.real(z2)

    grid_y[:, 0] = np.imag(z1)
    grid_y[0, :] = np.imag(z2)
    grid_y[:, eta_max - 1] = np.imag(z3)
    grid_y[xi_max - 1, :] = np.imag(z2)

    diff_x_xi = lambda i, j: 0.5 * (grid_x[i+1, j] - grid_x[i-1, j])
    diff_y_xi = lambda i, j: 0.5 * (grid_y[i+1, j] - grid_y[i-1, j])
    diff_x_eta = lambda i, j: 0.5 * (grid_x[i, j+1] - grid_x[i, j-1])
    diff_y_eta = lambda i, j: 0.5 * (grid_y[i, j+1] - grid_y[i, j-1])

    Aij = lambda i, j: (diff_x_eta(i, j)**2 + diff_y_eta(i, j)**2)
    Bij = lambda i, j: (diff_x_xi(i, j) * diff_x_eta(i, j) + diff_y_xi(i, j) * diff_y_eta(i, j))
    Cij = lambda i, j: (diff_x_xi(i, j)**2 + diff_y_xi(i, j)**2)

    point_number = (xi_max - 2) * (eta_max - 2)
    Ni = xi_max - 2
    Nj = eta_max - 2
    matrix = lil_matrix((2*point_number, 2*point_number))

    for iter in range(100):
        # matrix & rhsの準備
        rhs = np.zeros(2 * point_number)
        for J in range(point_number):
            row = floor(J / Nj)
            i = J - row * Nj    # aij対策で+1  # matrixの0番はgrid_xyの1番に相当
            j = row + 1 # aij対策で+1

            aij = Aij(i, j)
            bij = Bij(i,j)
            cij = Cij(i, j)

            matrix[J, J] = -2.0 * (aij + cij)
            matrix[J + point_number, J + point_number] = -2.0 * (aij + cij)
            # x-direction
            if J > 0:
                matrix[J, J-1] = aij
                matrix[J + point_number, J + point_number - 1] = aij
            if J < point_number-1:
                matrix[J, J+1] = aij
                matrix[J + point_number, J + point_number + 1] = aij

            if J > Nj:
                matrix[J, J-Nj] = cij
                matrix[J + point_number, J + point_number - Nj] = cij
            if J < point_number - 1 - Nj:
                matrix[J, J+Nj] = cij
                matrix[J + point_number, J + point_number + Nj] = cij

            if J > (Nj - 1):
                matrix[J, J-(Nj-1)] = 2.0 * bij
                matrix[J + point_number, J + point_number - (Nj - 1)] = 2.0 * bij
            if J < point_number - 1 - (Nj - 1):
                matrix[J, J+(Nj-1)] = 2.0 * bij
                matrix[J + point_number, J + point_number + (Nj - 1)] = 2.0 * bij

            if J > (Nj + 1):
                matrix[J, J-(Nj+1)] = -2.0 * bij
                matrix[J + point_number, J + point_number - (Nj + 1)] = -2.0 * bij
            if J < point_number - 1 - (Nj + 1) - 1:
                matrix[J, J+(Nj+1)] = -2.0 * bij
                matrix[J + point_number, J + point_number + (Nj + 1)] = -2.0 * bij

            boundary = 0
            if i == 1:
                boundary += 1
            if i == Ni:
                boundary += 2
            if j == 1:
                boundary += 3
            if j == Nj:
                boundary += 7

            if boundary == 1:   # x0境界
                rhs[J] = 2.0 * bij * grid_x[0, j-1] - aij * grid_x[0, j] - 2.0 * bij * grid_x[0, j + 1]
                rhs[J + point_number] = 2.0 * bij * grid_y[0, j - 1] - aij * grid_y[0, j] - 2.0 * bij * grid_y[0, j + 1]

            if boundary == 3:   # y0境界
                rhs[J] = 2.0 * bij * (grid_x[i-1, 0] - grid_x[i+1, 0]) - cij * grid_x[i, 0]
                rhs[J + point_number] = 2.0 * bij * (grid_y[i - 1, 0] - grid_y[i + 1, 0]) - cij * grid_y[i, 0]

            if boundary == 2:   # xN境界
                rhs[J] = -2.0 * bij * grid_x[xi_max - 1, j - 1] - aij * grid_x[xi_max - 1, j] + 2.0 * bij * grid_x[xi_max-1, j + 1]
                rhs[J + point_number] = -2.0 * bij * grid_y[xi_max - 1, j - 1] - aij * grid_y[xi_max - 1, j] + 2.0 * bij * grid_y[xi_max - 1, j + 1]

            if boundary == 7:   # yN境界
                rhs[J] = -2.0 * bij * (grid_x[i - 1, eta_max-1] - grid_x[i + 1, eta_max-1]) - cij * grid_x[i, eta_max-1]
                rhs[J + point_number] = -2.0 * bij * (grid_y[i - 1, eta_max-1] - grid_y[i + 1, eta_max-1]) - cij * grid_y[i, eta_max-1]

            if boundary == 4:   # x0 and y0
                rhs[J] = 2.0 * bij * (grid_x[0, 0] - grid_x[2, 0] - grid_x[0, 2]) - aij * grid_x[0, 1] - cij * grid_x[1, 0]
                rhs[J + point_number] = 2.0 * bij * (grid_y[0, 0] - grid_y[2, 0] - grid_y[0, 2]) - aij * grid_y[0, 1] - cij * grid_y[1, 0]

            if boundary == 8:  # x0 and yN
                rhs[J] = 2.0 * bij * (grid_x[0, eta_max-3] - grid_x[0, eta_max-1] + grid_x[2, eta_max-1]) - aij * grid_x[0, eta_max-2] -cij * grid_x[1, eta_max-1]
                rhs[J + point_number] = 2.0 * bij * (grid_y[0, eta_max - 3] - grid_y[0, eta_max - 1] + grid_y[2, eta_max - 1]) - aij * grid_y[0, eta_max - 2] - cij * grid_y[1, eta_max - 1]

            if boundary == 5:   # y0 and xN
                rhs[J] = 2.0 * bij * (grid_x[xi_max-3, 0] - grid_x[xi_max-1, 0] + grid_x[xi_max-1, 2]) - aij * grid_x[xi_max-1, 1] - cij * grid_x[xi_max-2, 0]
                rhs[J + point_number] = 2.0 * bij * (grid_y[xi_max - 3, 0] - grid_y[xi_max - 1, 0] + grid_y[xi_max - 1, 2]) - aij * grid_y[xi_max - 1, 1] - cij * grid_y[xi_max - 2, 0]

            if boundary == 9:   # xN and yN
                rhs[J] = 2.0 * bij * (-grid_x[xi_max-1, eta_max-2] - grid_x[xi_max-3, eta_max-1] + grid_x[xi_max-1, eta_max-1]) - aij * grid_x[xi_max-1, eta_max-2] - cij * grid_x[xi_max-2, eta_max-1]
                rhs[J + point_number] = 2.0 * bij * (-grid_y[xi_max - 1, eta_max - 2] - grid_y[xi_max - 3, eta_max - 1] + grid_y[xi_max - 1, eta_max - 1]) - aij * grid_y[xi_max - 1, eta_max - 2] - cij * grid_y[xi_max - 2, eta_max - 1]

        xy = bicg(matrix, rhs)[0]

        grid_x[1:xi_max-1, 1:eta_max-1] = xy[:point_number].reshape(xi_max-2, -1).T
        grid_y[1:xi_max-1, 1:eta_max-1] = xy[point_number:].reshape(xi_max-2, -1).T

        plt.plot(grid_x.reshape(-1), grid_y.reshape(-1), "x")
        plt.show()


    # return grid_x, grid_y
"""

"""
def make_grid(z1, z2, z3):
    xi_max = z1.shape[0]    # xi方向の格子点数
    eta_max = z2.shape[0]   # eta方向の格子点数

    grid_x = np.zeros((xi_max, eta_max))    # x座標格納
    grid_y = np.zeros((xi_max, eta_max))    # y座標格納
    # 境界条件適用
    grid_x[:, 0] = np.real(z1)  # 底辺
    grid_x[0, :] = np.real(z2)  # 左辺
    grid_x[:, eta_max - 1] = np.real(z3)    # 上辺
    grid_x[xi_max - 1, :] = np.real(z2)

    grid_y[:, 0] = np.imag(z1)
    grid_y[0, :] = np.imag(z2)
    grid_y[:, eta_max - 1] = np.imag(z3)
    grid_y[xi_max - 1, :] = np.imag(z2)
    # 計算準備
    rhs_x = np.zeros((xi_max-2, eta_max-2))   # δxに関する方程式の右辺格納
    rhs_y = np.zeros((xi_max-2, eta_max-2))   # δyに関する方程式の右辺格納
    mid_x = np.zeros((xi_max-2, eta_max-2))   # δxに関する方程式の中間解格納
    mid_y = np.zeros((xi_max-2, eta_max-2))   # δyに関する方程式の中間解格納
    del_x = np.zeros((xi_max - 2, eta_max - 2))  # δxに関する方程式の解格納
    del_y = np.zeros((xi_max - 2, eta_max - 2))  # δyに関する方程式の解格納

    mXIdiag = np.zeros(eta_max-2)  # xi方向に対応する3重対角行列の対角成分格納用
    mXIside = np.zeros(eta_max-2) # xi方向に対応する3重対角行列の左右成分格納用

    mETAdiag = np.zeros(xi_max-2) # eta方向に対応する3重対角行列の対角成分格納用
    mETAside = np.zeros(xi_max-2)  # eta方向に対応する3重対角行列の左右成分格納用

    diff_x_xi = lambda i, j: 0.5 * (grid_x[i+1, j] - grid_x[i-1, j])
    diff_y_xi = lambda i, j: 0.5 * (grid_y[i+1, j] - grid_y[i-1, j])
    diff_x_eta = lambda i, j: 0.5 * (grid_x[i, j+1] - grid_x[i, j-1])
    diff_y_eta = lambda i, j: 0.5 * (grid_y[i, j+1] - grid_y[i, j-1])

    Aij = lambda i, j: (diff_x_eta(i, j)**2 + diff_y_eta(i, j)**2)
    Bij = lambda i, j: (diff_x_xi(i, j) * diff_x_eta(i, j) + diff_y_xi(i, j) * diff_y_eta(i, j))
    Cij = lambda i, j: (diff_x_xi(i, j)**2 + diff_y_xi(i, j)**2)

    diff_x_xixi = lambda i, j: grid_x[i+1, j] - 2.0 * grid_x[i, j] + grid_x[i-1, j]
    diff_y_xixi = lambda i, j: grid_y[i+1, j] - 2.0 * grid_y[i, j] + grid_y[i-1, j]

    diff_x_etaeta = lambda i, j: grid_x[i, j+1] - 2.0 * grid_x[i, j] + grid_x[i, j-1]
    diff_y_etaeta = lambda i, j: grid_y[i, j+1] - 2.0 * grid_y[i, j] + grid_y[i, j-1]

    diff_x_xieta = lambda i, j: grid_x[i+1, j+1] - grid_x[i+1, j-1] - grid_x[i-1, j+1] + grid_x[i-1, j-1]
    diff_y_xieta = lambda i, j: grid_y[i+1, j+1] - grid_y[i+1, j-1] - grid_y[i-1, j+1] + grid_y[i-1, j-1]

    delta_t = 0.1

    for iter in range(100):
        #rhs計算
        for i in range(1, xi_max-1):
            for j in range(1, eta_max-1):
                aij = Aij(i, j)
                bij = Bij(i,j)
                cij = Cij(i, j)

                rhs_x[i-1, j-1] = - delta_t * (aij * diff_x_xixi(i, j)
                                               - 2.0 * bij * diff_x_xieta(i, j)
                                               + cij * diff_x_etaeta(i, j))

                rhs_y[i-1, j-1] = - delta_t * (aij * diff_y_xixi(i, j)
                                               - 2.0 * bij * diff_y_xieta(i, j)
                                               + cij * diff_y_etaeta(i, j))

        # ADI 1st step
        for i in range(1, xi_max-1):
            for j in range(1, eta_max-1):
                aij = Aij(i, j)
                mXIdiag[j-1] = 1.0 - 2.0*delta_t*aij
                mXIside[j-1] = delta_t*aij

            mid_x[i-1, :] = tridiagonal_matrix_algorithm(mXIside, mXIdiag, mXIside, rhs_x[i-1, :], eta_max-2)
            # print(mid_x[i-1, :])
            matrix = np.zeros((eta_max-2, eta_max-2))
            matrix[0, 0] = 1.0 - 2.0*delta_t*Aij(1, 1)
            matrix[0, 1] = delta_t*Aij(1, 1)
            for k in range(1,eta_max-3):
                aij = Aij(k+1, k+1)
                matrix[k, k-1] = delta_t*aij
                matrix[k, k] = 1.0 - 2.0*delta_t*aij
                matrix[k, k+1] = delta_t*aij
            matrix[eta_max-3, eta_max-3] = 1.0 - 2.0*delta_t*Aij(1, eta_max-2)
            matrix[eta_max - 3, eta_max - 4] = delta_t * Aij(1, eta_max-2)
            mid_y[i-1, :] = tridiagonal_matrix_algorithm(mXIside, mXIdiag, mXIside, rhs_y[i-1, :], eta_max-2)

        # ADI 2nd step
        for j in range(1, eta_max-1):
            for i in range(1, xi_max-1):
                cij = Cij(i, j)
                mETAdiag[i-1] = 1.0 - 2.0 * delta_t * cij
                mETAside[i-1] = delta_t * cij

            del_x[:, j-1] = tridiagonal_matrix_algorithm(mETAside, mETAdiag, mETAside, mid_x[:, j-1], xi_max-2)
            del_y[:, j-1] = tridiagonal_matrix_algorithm(mETAside, mETAdiag, mETAside, mid_y[:, j-1], xi_max-2)


        # delta-form
        grid_x[1:xi_max-1, 1:eta_max-1] += del_x
        grid_y[1:xi_max-1, 1:eta_max-1] += del_y

        res = (np.sum(np.abs(del_x)) + np.sum(np.abs(del_y)))
        print(np.argmax(np.abs(del_x)), np.argmax(np.argmin(del_y)))

        print(res)
        plt.plot(grid_x.reshape(-1), grid_y.reshape(-1), "x")
        plt.show()
        if res < 0.001:
            break
"""


"""
# 複素数列z1, z2,...を, 2倍の長さの実数列x1, y1, x2, y2, ...に変換
def line_up_z2xy(z, two_rows=False):
    
x = np.real(z).reshape(1, -1)
y = np.imag(z).reshape(1, -1)
xy = np.vstack((x, y)).T.reshape(-1)
return xy

if two_rows:
    return np.vstack((np.real(z).reshape(1, -1), np.imag(z).reshape(1, -1))).T
else:
    return np.vstack((np.real(z).reshape(1, -1), np.imag(z).reshape(1, -1))).T.reshape(-1)


# 物体表面座標点列を内側に縮小し，0番目の仮データを用意する
def offset_surface(z):
size = z.shape[0] - 1
delta = z[1:] - z[:size]
theta = np.zeros(size)
theta[0] = 0.5 * np.angle(-delta[size-1]/delta[0]) + np.angle(delta[0])
theta[1:] = 0.5 * np.angle(-delta[:size-1]/delta[1:]) + np.angle(delta[1:])
offset_quantity = np.average(np.abs(delta))
z0 = np.zeros_like(z)
z0[:size] = z[:size] + offset_quantity * np.exp(1j * theta)
z0[size] = z0[0]
return z0

# 係数行列を計算
def made_coefficient_matrix(x0, x1, y0, y1, phi0, phi1, V0, V1):
def make_invA(i):
    detA = 4.0 / ((x1[i] - x0[i])**2 + (y1[i] - y0[i])**2)
    invA[0, 0] = detA * (x1[i] - x0[i])
    invA[0, 1] = detA * (y1[i] - y0[i])
    invA[1, 0] = detA * (y1[i] - y0[i])
    invA[1, 1] = - detA * (x1[i] - x0[i])
    return invA

def make_r(i):
    r[0] = -phi1[i]*V1[i]**2 - phi0[i]*V0[i]**2
    r[1] = V1[i] + V0[i]
    return r

size = x0.shape[0]
coefMat = np.zeros((2*size, 2*size))
const_vector = np.zeros(2*size)
invA = np.zeros((2, 2))
B = np.zeros((2, 2))
r = np.zeros(2)

# i = 0
invA = make_invA(0)
B[0, 0] = 0.5 * (x1[1] - x1[size-1])
B[0, 1] = 0.5 * (y1[1] - y1[size-1])
B[1, 0] = -0.5 * (y1[1] - y1[size-1])
B[1, 1] = 0.5 * (x1[1] - x1[size-1])
B *= 2
coefMat[0:2, 2*size - 2:2*size] = -1.0
coefMat[0:2, 0:2] = np.dot(invA, B)
coefMat[0:2, 2:4] = 1.0

r = make_r(0)
stabilizer = np.array([x1[1] - 2.0 * x1[0] + x1[size - 1], y1[1] - 2.0 * y1[0] + y1[size - 1]])
const_vector[0:2] = np.dot(invA, r + np.dot(B, np.array([x1[0], y1[0]]))) + stabilizer

for i in range(1, size-1):
    k = 2 * i # - 1
    invA = make_invA(i)
    B[0, 0] = 0.5 * (x1[i+1] - x1[i-1])
    B[0, 1] = 0.5 * (y1[i+1] - y1[i-1])
    B[1, 0] = -0.5 * (y1[i+1] - y1[i-1])
    B[1, 1] = 0.5 * (x1[i+1] - x1[i-1])
    B *= 2
    coefMat[k:k+2, k-2:k] = -1.0
    coefMat[k:k+2, k:k+2] = np.dot(invA, B)
    coefMat[k:k+2, k+2:k+4] = 1.0
    r = make_r(i)
    stabilizer = np.array([x1[i+1] - 2.0 * x1[i] + x1[i-1], y1[i+1] - 2.0 * y1[i] + y1[i-1]])
    const_vector[k:k+2] = np.dot(invA, r + np.dot(B, np.array([x1[i], y1[i]]))) + stabilizer

# i = size - 1
invA = make_invA(size-1)
B[0, 0] = 0.5 * (x1[0] - x1[size-2])
B[0, 1] = 0.5 * (y1[0] - y1[size-2])
B[1, 0] = -0.5 * (y1[0] - y1[size-2])
B[1, 1] = 0.5 * (x1[0] - x1[size-2])
B *= 2
coefMat[2*size-2:2*size, 2*size-4:2*size-2] = -1.0
coefMat[2*size-2:2*size, 2*size-2:2*size] = np.dot(invA, B)
coefMat[2*size-2:2*size, 0:2] = 1.0
r = make_r(size-1)
stabilizer = np.array([x1[0] - 2.0 * x1[size-1] + x1[size-2], y1[0] - 2.0 * y1[size-1] + y1[size-2]])
const_vector[2*size-2:2*size] = np.dot(invA, r + np.dot(B, np.array([x1[size-1], y1[size-1]]))) + stabilizer

return coefMat, const_vector

# 計算済みの閉曲線から一回り大きな閉曲線を求める
def get_next_closed_curve(z0, z1):
a = 1
"""
