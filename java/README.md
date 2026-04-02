# BeyonAI Framework Java Samples

本目录包含了使用 `by-framework-java` SDK 的多种 Java 示例，涵盖了从原生 Java SE 到 Spring Boot 的集成。

## 目录结构

- **[java-se-samples](./java-se-samples)**: 原生 Java SE 示例，包含基础的消息发送、服务注册/发现等。
- **[springboot-samples](./springboot-samples)**: 基于 Spring Boot 3.x 的集成示例，展示了如何在 Web 应用中自动管理服务生命周期。

## 准备工作

1. **Redis**: 确保本地正在运行 Redis 服务（默认端口 6379）。
2. **Java**: 需要 JDK 21 或更高版本。
3. **Maven**: 确保已安装并配置 Maven。

## 构建项目

在 `java` 根目录下运行以下命令构建所有模块：

```bash
mvn clean install
```

---

## 1. 启动 Spring Boot 示例

该模块演示了服务启动时自动向 Redis 注册，并在停止时注销。

### 命令行启动：
```bash
cd springboot-samples
mvn spring-boot:run
```

### 验证：
启动成功后，可以访问以下接口查看注册状态：
- http://localhost:8080/status

---

## 2. 启动原生 Java SE 示例

该模块包含多个独立的 `main` 函数示例。

### 注册服务示例：
```bash
cd java-se-samples
mvn exec:java -Dexec.mainClass="com.beyonai.byframework.samples.examples.ServiceRegistryExample"
```

### 发现服务示例（在另一个终端运行）：
```bash
cd java-se-samples
mvn exec:java -Dexec.mainClass="com.beyonai.byframework.samples.examples.ServiceDiscoveryExample"
```

### 发送消息示例：
```bash
cd java-se-samples
mvn exec:java -Dexec.mainClass="com.beyonai.byframework.samples.examples.SendMessageExample"
```

---

## 配置说明

所有示例均依赖于 `gateway-config.properties` 进行 Redis 连接配置。你可以分别在以下路径找到并修改它们：
- `springboot-samples/src/main/resources/gateway-config.properties`
- `java-se-samples/src/main/resources/gateway-config.properties`

> **注意**: 如果遇到鉴权超时，请检查 Redis `username` 和 `password` 是否与本地环境匹配或建议保持为空。
