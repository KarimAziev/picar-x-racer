import axios from "axios";

export const takePhoto = () => axios.get(`/api/camera/capture-photo`);
