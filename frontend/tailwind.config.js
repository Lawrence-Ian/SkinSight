export default {
  content: ["./index.html","./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        skin: { bg:"#FFFBF1", card:"#FFF2D0", a1:"#FFB2B2", a2:"#E36A6A", text:"#3D2B1F", muted:"#8B7355", border:"#F0DEB8" }
      },
      fontFamily: { display:["'Playfair Display'","serif"], body:["'DM Sans'","sans-serif"] }
    }
  },
  plugins: []
}
