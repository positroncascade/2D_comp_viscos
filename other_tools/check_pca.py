# coding: utf-8
import numpy as np
from read_training_data_viscos import read_csv_type3
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from scipy.spatial import distance

def pca(source, fname_lift_train, fname_lift_test, fname_shape_train, fname_shape_test, standardized=True):
    
    # r_rate = [1, 2, 4, 8]
    r_rate = [1]
    # s_rate = [2, 4, 8]
    s_rate = [2]
    # s_skiptype = [True, False]
    s_skiptype = True
    # r_rate = [1, 2]
    # r_rate = [4, 8]
    # r_rate = [16, 32]
    # r_rate = [64, 160]

    for sr in s_rate:
        for rr in r_rate:
            if rr == 1:
                s_odd = 0  # 全部読みだす
            elif fname_shape_train.find("fourier") != -1:
                s_odd = 3  # 前方から読み出す(fourier用)
            else:
                s_odd = 4  # 全体にわたって等間隔に読み出す(equidistant, dense用)

            if standardized:
                X_train, y_train, scalar = read_csv_type3(source, fname_lift_train, fname_shape_train, shape_odd = s_odd, read_rate = rr, total_data = 0, return_scalar = True)
                X_test, y_test = read_csv_type3(source, fname_lift_test, fname_shape_test, shape_odd = s_odd,
                                                read_rate = rr, total_data = 0, scalar = scalar)
            else:
                X_train, y_train = read_csv_type3(source, fname_lift_train, fname_shape_train, shape_odd = s_odd, read_rate = rr, total_data = 0, regularize = False)
                X_test, y_test = read_csv_type3(source, fname_lift_test, fname_shape_test, shape_odd = s_odd,
                                                read_rate = rr, total_data = 0, regularize = False)
    
            # cos_distance(X_train, X_test)
            plot_X_train_average=False
            if plot_X_train_average:
                ave = np.average(X_train, axis = 0)
                print(ave.shape)
                fig = plt.figure()
                ax = fig.add_subplot(1,1,1)
                ax.plot(np.arange(202) + 1, ave, marker="o", color="mediumvioletred", label="Non-Standardized Vector", linestyle="None")
                ax.set_yscale("log")
                ax.legend()
                ax.set_title("Average Scale of Vector Components")
                ax.set_xlabel("Number of Vector Components")
                ax.set_ylabel("Order of magnitude")
                plt.show()
                exit()
            pca = PCA(n_components = 10)
            pca.fit(X_train)
            transformed = pca.fit_transform(X_train)
            print(pca.explained_variance_ratio_)
            print(sum(pca.explained_variance_ratio_))
            
            if standardized:
                plot_var_ratio = True
                if plot_var_ratio:
                    pca2 = PCA(n_components = 10)
                    X_train2, y_train2 = read_csv_type3(source, fname_lift_train, fname_shape_train, shape_odd = s_odd,
                                                      read_rate = rr, total_data = 0, regularize = False)
                    pca2.fit(X_train2)
                    x = np.arange(10) + 1
                    fig = plt.figure()
                    ax = fig.add_subplot(1, 1, 1)
                    ax.plot(x, pca2.explained_variance_ratio_, marker="o", color="mediumvioletred",  label="Non-Standardized")
                    ax.plot(x, pca.explained_variance_ratio_, marker="*", color = "dodgerblue", label = "Standardized")
                    ax.legend(bbox_to_anchor = (0, 1), loc = "upper left", borderaxespad = 1, fontsize = 12)
                    ax.set_title("PCA of Standardized Dataset")
                    ax.set_xlabel("Nth principal component")
                    ax.set_ylabel("Explained Variance Ratio")
                    ax.set_xlim(1,10)
                    ax.set_ylim(0,1)
                    plt.show()

            transformed_test = pca.fit_transform(X_test)

            fig = plt.figure()
            ax = fig.add_subplot(1, 1, 1)
            ax.scatter(transformed[:,0], transformed[:,1], alpha=0.3, color="dodgerblue", label = "Training")
            ax.scatter(transformed_test[:, 0], transformed_test[:, 1], marker="*", alpha=0.5, color="mediumvioletred", label = "Test")
            ax.legend(bbox_to_anchor = (0, 1), loc = "upper left", borderaxespad = 1, fontsize = 12)
            ax.set_title("PCA of Standardized Dataset")
            ax.set_xlabel("1st principal component")
            ax.set_ylabel("2nd principal component")
            plt.show()
            fig.show()


# X_train & X_test :(N_samples, N_features)
def cos_distance(X_train, X_test):
   
    # 1 - (u,v)/(|u||v|)が得られるため区間は[0,2]
    dist_ij = distance.cdist(X_train, X_test, metric = "cosine")

    dist_ij = -(dist_ij - 1.0)  # cos類似度の絶対値に変換
    mean = np.mean(dist_ij)
    var = np.var(dist_ij)

    binnum = 100
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ax.hist(dist_ij.reshape(-1), bins=binnum,range=(-1,1), label="Cosine Distance", density = True)
    
    ax_yticklocs = ax.yaxis.get_ticklocs()  # 目盛りの情報を取得
    ax_yticklocs = list(map(lambda x: x * len(range(-1, 1)) * 1.0 / binnum, ax_yticklocs))  # 元の目盛りの値にbinの幅を掛ける
    ax.yaxis.set_ticklabels(list(map(lambda x: "%0.3f" % x, ax_yticklocs)))
    
    ax.set_title("Cosine Distance Histogram: Training Data - Test Data (Standardized)")
    
    ax.set_xlabel("Cosine Distance")
    ax.set_ylabel("Rate of Appearance")
    ax.set_xlim(-1,1)

    fig.show()
    plt.show()

    dist_ij = np.abs(dist_ij)
    min = np.min(dist_ij)
    max = np.max(dist_ij)
    print(min, max)
    print(mean, var)
    
if __name__ == '__main__':
    
    source = "G:\\Toyota\\Data\\Compressible_Invicid\\training_data\\"
    fname_lift_train = "NACA4\\s1122_e9988_s4_a014.csv"
    fname_lift_test = "NACA5\\s21011_e25190_s1_a014.csv"
    fname_shape_train = "NACA4\\shape_fourier_1112_9988_s04.csv"
    fname_shape_test = "NACA5\\shape_fourier_21011_25190_s1.csv"

    pca(source, fname_lift_train, fname_lift_test, fname_shape_train, fname_shape_test, standardized = False)
    