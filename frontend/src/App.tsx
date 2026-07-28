import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import TaskCreate from "./pages/TaskCreate/TaskCreate";
import TaskDetail from "./pages/TaskDetail/TaskDetail";
import EvalCompare from "./pages/EvalCompare/EvalCompare";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<TaskCreate />} />
          <Route path="/tasks/:taskId" element={<TaskDetail />} />
          <Route path="/eval" element={<EvalCompare />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
