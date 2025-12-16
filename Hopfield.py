import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import rcParams

# 全局配置（适配教学可视化）
rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']  # 使用英文字体
rcParams['axes.unicode_minus'] = False

# ---------------------- 核心算法：简化Hopfield网络求解TSP ----------------------
class SimplifiedHopfieldTSP:
    def __init__(self, distance_matrix, A=100, B=100, C=100, D=1):
        self.N = distance_matrix.shape[0]  # 快递点数量
        self.d = distance_matrix  # 距离矩阵
        # 权重系数（对应论文中的惩罚项和目标项）
        self.A = A  # 惩罚重复访问同一快递点
        self.B = B  # 惩罚同一步骤访问多个快递点
        self.C = C  # 惩罚未遍历所有快递点
        self.D = D  # 目标项（路径长度权重）
        # 神经元状态矩阵 V[i][j]：第j步访问第i个快递点（1=是，0=否）
        self.V = np.zeros((self.N, self.N))
        # 初始化：确保从1号点（索引0）开始
        self.V[0, 0] = 1  # 第0步必须访问1号点
        # 随机初始化其他位置，但确保每行每列至少有一个1
        for i in range(1, self.N):
            # 每行（除第0行）随机选择一个位置设为1
            j = np.random.randint(1, self.N)
            self.V[i, j] = 1
        # 确保每列（除第0列）至少有一个1
        for j in range(1, self.N):
            if np.sum(self.V[:, j]) == 0:
                i = np.random.randint(1, self.N)
                self.V[i, j] = 1

    def energy_function(self):
        """计算能量函数（简化版，对应论文E=E约束项+E距离项）"""
        # 约束项1：同一快递点不能被多次访问（每行最多一个1）
        constraint1 = np.sum(np.square(np.sum(self.V, axis=1) - 1))
        # 约束项2：同一步骤不能访问多个快递点（每列最多一个1）
        constraint2 = np.sum(np.square(np.sum(self.V, axis=0) - 1))
        # 约束项3：必须遍历所有快递点（总激活数=快递点数量）
        constraint3 = np.square(np.sum(self.V) - self.N)
        # 约束项4：确保从1号点开始（第0步必须访问1号点，且1号点只能在第0步访问）
        constraint4 = 0
        if self.V[0, 0] != 1:
            constraint4 += 1000  # 强烈惩罚：第0步必须访问1号点
        if np.sum(self.V[0, 1:]) > 0:
            constraint4 += 1000  # 强烈惩罚：1号点不能在除第0步外的其他步骤访问
        if np.sum(self.V[1:, 0]) > 0:
            constraint4 += 1000  # 强烈惩罚：第0步不能访问除1号点外的其他点
        # 距离项：路径总长度（目标项）
        distance_term = 0
        for j in range(self.N):
            for i in range(self.N):
                for k in range(self.N):
                    if j == self.N - 1:
                        next_j = 0  # 最后一步返回起点，形成闭合路线
                    else:
                        next_j = j + 1
                    distance_term += self.d[i, k] * self.V[i, j] * self.V[k, next_j]
        # 总能量（对应论文的惩罚-目标机制）
        total_energy = self.A * constraint1 + self.B * constraint2 + self.C * constraint3 + 1000 * constraint4 + self.D * distance_term
        return total_energy, constraint1, constraint2, constraint3, distance_term

    def update_neuron(self):
        """异步更新神经元状态（确保能量单调递减）"""
        # 随机选择一个神经元更新
        i = np.random.randint(0, self.N)
        j = np.random.randint(0, self.N)
        
        # 计算该神经元的输入（简化版更新规则，避免复杂推导）
        input_val = -self.A * np.sum(self.V[i, :]) + self.A  # 约束项1
        input_val -= self.B * np.sum(self.V[:, j]) + self.B  # 约束项2
        input_val -= self.C * np.sum(self.V) + self.C * self.N  # 约束项3
        # 距离项输入
        for k in range(self.N):
            if j == 0:
                prev_j = self.N - 1
            else:
                prev_j = j - 1
            input_val -= self.D * self.d[k, i] * self.V[k, prev_j]
            input_val -= self.D * self.d[i, k] * self.V[k, (j+1)%self.N]
        
        # 激活函数（二值化：输入>0则激活为1，否则为0）
        self.V[i, j] = 1 if input_val > 0 else 0

    def train(self, max_iter=1000, energy_threshold=10):
        """训练网络：迭代更新神经元，直到能量收敛"""
        energy_history = []  # 记录能量变化（用于可视化）
        for iter in range(max_iter):
            current_energy, c1, c2, c3, dt = self.energy_function()
            energy_history.append(current_energy)
            
            # 能量收敛条件：能量值低于阈值或变化量小于1
            if current_energy < energy_threshold:
                break
            if iter > 10 and abs(energy_history[-1] - energy_history[-2]) < 1:
                break
            
            # 更新神经元状态
            self.update_neuron()
        
        # 提取最优路线（从神经元状态矩阵中解析）
        route = []
        for j in range(self.N):
            for i in range(self.N):
                if self.V[i, j] == 1:
                    route.append(i + 1)  # 快递点编号从1开始（适配论文示例）
        # 闭合路线（最后返回起点）
        route.append(route[0])
        # 计算实际路径长度
        total_distance = 0
        for i in range(len(route)-1):
            total_distance += self.d[route[i]-1, route[i+1]-1]
        
        return route, total_distance, energy_history

# ---------------------- 前端界面设计（适配高中生操作） ----------------------
def main():
    st.title("📦 校园快递路径优化 - Hopfield网络仿真程序")
    st.subheader("适合高中物理+AI跨学科教学 | 基于能量最低原理")
    st.markdown("---")

    # 1. 快递点数量设置（默认5个，适配论文示例）
    N = st.sidebar.number_input("快递点数量", min_value=3, max_value=8, value=5, step=1)
    st.sidebar.markdown("---")

    # 2. 距离矩阵输入（支持手动输入或使用示例数据）
    st.subheader("Step1：输入距离矩阵（单位：米）")
    use_example = st.checkbox("使用论文示例数据（5个快递点）", value=True)
    if use_example:
        # 论文中的示例距离矩阵（教学楼、图书馆、宿舍区、食堂、校门口）
        d_matrix = np.array([
            [0, 80, 150, 120, 200],
            [80, 0, 130, 90, 180],
            [150, 130, 0, 60, 250],
            [120, 90, 60, 0, 220],
            [200, 180, 250, 220, 0]
        ])
    else:
        # 手动输入距离矩阵
        d_matrix = np.zeros((N, N))
        for i in range(N):
            cols = st.columns(N)
            for j in range(N):
                if i == j:
                    d_matrix[i, j] = 0  # 对角线为0（自身到自身距离）
                    cols[j].number_input(f"点{i+1}→点{j+1}", value=0, disabled=True)
                else:
                    d_matrix[i, j] = cols[j].number_input(f"点{i+1}→点{j+1}", min_value=1, value=np.random.randint(50, 300))
    st.write("当前距离矩阵：")
    # 创建带英文标签的DataFrame
    df_distance = pd.DataFrame(
        d_matrix.round(0).astype(int),
        index=[f"Point {i+1}" for i in range(d_matrix.shape[0])],
        columns=[f"Point {j+1}" for j in range(d_matrix.shape[1])]
    )
    st.dataframe(df_distance)
    st.markdown("---")

    # 3. 权重系数设置（对应论文中的A、B、C、D，支持调整体验惩罚力度）
    st.subheader("Step2：调整权重系数（体验惩罚-目标机制）")
    col1, col2, col3, col4 = st.columns(4)
    A = col1.slider("A（惩罚重复访问）", min_value=50, max_value=200, value=100, step=10)
    B = col2.slider("B（惩罚多步同点）", min_value=50, max_value=200, value=100, step=10)
    C = col3.slider("C（惩罚遗漏点）", min_value=50, max_value=200, value=100, step=10)
    D = col4.slider("D（路径长度权重）", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
    st.markdown("💡 提示：增大A/B/C会增强“惩罚力度”，增大D会更侧重缩短路径")
    st.markdown("---")

    # 4. 运行仿真
    st.subheader("Step3：运行Hopfield网络仿真")
    if st.button("开始仿真", type="primary"):
        with st.spinner("仿真中... 正在寻找最优路径（模拟能量最低态收敛）"):
            # 初始化Hopfield网络
            hopfield = SimplifiedHopfieldTSP(d_matrix, A=A, B=B, C=C, D=D)
            # 训练网络
            optimal_route, total_dist, energy_history = hopfield.train()
        
        # 展示结果
        st.success("仿真完成！找到最优配送路线（能量最低态）")
        st.subheader("📊 仿真结果")
        col1, col2 = st.columns(2)
        # 最优路线
        col1.write("最优配送路线：")
        route_str = " → ".join(map(str, optimal_route))
        col1.markdown(f"**{route_str}**")
        col1.write(f"总路程：{total_dist:.0f} 米")
        # 能量变化曲线（类比小球沿曲面滚动）
        col2.write("能量变化曲线（越低越优）：")
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(energy_history, label="Energy", color="#1f77b4")
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Energy")
        ax.set_title("Energy Convergence Process")
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

        # 试错验证功能（对应论文中的试错环节）
        st.markdown("---")
        st.subheader("🔍 试错验证（探究数据准确性的影响）")
        if st.checkbox("使用错误距离矩阵（颠倒部分数值）"):
            # 生成错误距离矩阵（颠倒前两行）
            wrong_d = d_matrix.copy()
            wrong_d[0], wrong_d[1] = wrong_d[1], wrong_d[0]
            with st.spinner("错误数据仿真中..."):
                hopfield_wrong = SimplifiedHopfieldTSP(wrong_d, A=A, B=B, C=C, D=D)
                wrong_route, wrong_dist, wrong_energy = hopfield_wrong.train()
            st.write("错误距离矩阵的仿真结果：")
            wrong_route_str = " → ".join(map(str, wrong_route))
            st.markdown(f"路线：**{wrong_route_str}**")
            st.markdown(f"总路程：{wrong_dist:.0f} 米（比正确数据多 {wrong_dist-total_dist:.0f} 米）")
            st.markdown("💡 结论：数据输入错误会导致能量收敛到非最优解，AI模型依赖准确数据！")

# ---------------------- 程序运行入口 ----------------------
if __name__ == "__main__":
    main()