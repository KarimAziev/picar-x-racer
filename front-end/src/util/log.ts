export const logToElement = (text: string) => {
  console.log(text);
  const parent = document.querySelector('.logs');
  const elem = document.createElement('li');
  elem.textContent = text;
  parent?.appendChild(elem);
  // add scrolling

  elem?.scrollIntoView();
};
