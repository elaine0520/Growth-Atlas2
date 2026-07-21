import { Component, ErrorInfo, ReactNode } from "react";

interface Props { children: ReactNode }
interface State { failed: boolean }

class AppErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Growth Atlas render failure", error.name, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="loading-screen" role="alert">
        <section>
          <h1>页面暂时无法显示</h1>
          <p>你的数据已经保存在服务端。请刷新页面恢复当前步骤。</p>
          <button className="primary-button" onClick={() => window.location.reload()}>重新加载</button>
        </section>
      </main>
    );
  }
}

export default AppErrorBoundary;
