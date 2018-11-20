# -- coding: utf-8 --
import os
import re

def main(mode):
    if mode == "MPI":
        compiler = "mpif90"
    else:
        compiler = "ifort"
    CFLAGS_ifort = "CFLAGS = -Wall -check uninit -check pointers -check bounds -check all -inline-level=0 -O0 -traceback -warn all -ftrapuv -debug full -zero -check uninit -check pointers -check bounds -check all -O0 -traceback -warn interfaces -warn all -ftrapuv -debug full -qopenmp -module $(OBJS_DIR) $(IDIR)\n"
    LFLAGS_ifort = "LFLAGS = -qopenmp -s\n"

    if os._exists("Makefile"):
        os.replace("Makefile", "Makefile_win")
        flag = 0
        with open(file="Makefile_win", mode="r") as fw:
            with open(file="Makefile", mode="w") as fl:
                for row in fw:
                    line = row

                    if line.startswith("EXE"):
                        line = "EXE = EulerSolver2\n"
                        flag = 1

                    if flag == 1:
                        if line.startswith("FC"):
                            line = "FC = " + compiler + "\n"
                        if line.startswith("LD"):
                            line = "LD = " + compiler + "\n"
                        if line.startswith("CFLAGS"):
                            line = CFLAGS_ifort

                        if line.startswith("LFLAGS"):
                            line = LFLAGS_ifort
                            flag = 0
                    fl.write(line)


if __name__ == '__main__':
    mode = "ifort"
    #mode = "MPI"
    main(mode)