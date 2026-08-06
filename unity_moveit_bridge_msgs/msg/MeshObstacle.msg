string id
geometry_msgs/Pose pose

# 是否携带mesh数据（注册阶段 true；仅更新位姿阶段 false）
bool send_mesh

# mesh数据（仅 send_mesh=true 时有效）
float32[] vertices_xyz   # 展平数组: x0,y0,z0,x1,y1,z1,...
uint32[] triangles       # 三角形索引: i0,i1,i2,i3,i4,i5,...

# 可选：缩放（Unity本地缩放传过来）
float32 scale_x
float32 scale_y
float32 scale_z