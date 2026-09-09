namespace ns {
  export function fn(): void {}
}

function outer(): void {
  function inner(): void {}
  inner();
}

const handlers = {
  onClick: function () {},
  onBlur() {},
};

Store.reset = function () {};
module.exports.legacy = function () {};
module.exports = function () {};

const doubled = [1, 2].map((n) => n * 2);

(function () {
  outer();
})();

export default (value: string) => value;
